import os
import sys
import json
import asyncio
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv()

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
	os.getenv("SUPABASE_URL"),
	os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class ProcessedChunk:
	url: str
	chunk_number: int
	title: str
	summary: str
	content: str
	metadata: Dict[str, Any]
	embedding: List[float]

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
	"""Split text into chunks, respecting code blocks and paragraphs."""
	chunks = []
	start = 0
	text_length = len(text)

	while start < text_length:
		end = start + chunk_size
		if end >= text_length:
			chunks.append(text[start:].strip())
			break

		chunk = text[start:end]
		code_block = chunk.rfind('```')
		if code_block != -1 and code_block > chunk_size * 0.3:
			end = start + code_block
		elif '\n\n' in chunk:
			last_break = chunk.rfind('\n\n')
			if last_break > chunk_size * 0.3:
				end = start + last_break
		elif '. ' in chunk:
			last_period = chunk.rfind('. ')
			if last_period > chunk_size * 0.3:
				end = start + last_period + 1

		chunk = text[start:end].strip()
		if chunk:
			chunks.append(chunk)
		start = max(start + 1, end)

	return chunks

async def get_title_and_summary(chunk: str, url: str) -> Dict[str, str]:
	"""Extract title and summary using GPT-4."""
	system_prompt = """You are an AI that extracts titles and summaries from documentation chunks.
	Return a JSON object with 'title' and 'summary' keys.
	For the title: If this seems like the start of a document, extract its title. If it's a middle chunk, derive a descriptive title.
	For the summary: Create a concise summary of the main points in this chunk.
	Keep both title and summary concise but informative."""
	
	try:
		response = await openai_client.chat.completions.create(
			model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": f"URL: {url}\n\nContent:\n{chunk[:1000]}..."}
			],
			response_format={ "type": "json_object" }
		)
		return json.loads(response.choices[0].message.content)
	except Exception as e:
		print(f"Error getting title and summary: {e}")
		return {"title": "Error processing title", "summary": "Error processing summary"}

async def get_embedding(text: str) -> List[float]:
	"""Get embedding vector from OpenAI."""
	try:
		response = await openai_client.embeddings.create(
			model="text-embedding-3-small",
			input=text
		)
		return response.data[0].embedding
	except Exception as e:
		print(f"Error getting embedding: {e}")
		return [0] * 1536

async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
	"""Process a single chunk of text."""
	extracted = await get_title_and_summary(chunk, url)
	embedding = await get_embedding(chunk)
	
	metadata = {
		"source": "ultravox_docs",
		"chunk_size": len(chunk),
		"crawled_at": datetime.now(timezone.utc).isoformat(),
		"url_path": urlparse(url).path
	}
	
	return ProcessedChunk(
		url=url,
		chunk_number=chunk_number,
		title=extracted['title'],
		summary=extracted['summary'],
		content=chunk,
		metadata=metadata,
		embedding=embedding
	)

async def insert_chunk(chunk: ProcessedChunk):
	"""Insert a processed chunk into Supabase."""
	try:
		data = {
			"url": chunk.url,
			"chunk_number": chunk.chunk_number,
			"title": chunk.title,
			"summary": chunk.summary,
			"content": chunk.content,
			"metadata": chunk.metadata,
			"embedding": chunk.embedding
		}
		
		result = supabase.table("site_pages").insert(data).execute()
		print(f"Inserted chunk {chunk.chunk_number} for {chunk.url}")
		return result
	except Exception as e:
		print(f"Error inserting chunk: {e}")
		return None

async def process_and_store_document(url: str, markdown: str):
	"""Process a document and store its chunks in parallel."""
	chunks = chunk_text(markdown)
	tasks = [process_chunk(chunk, i, url) for i, chunk in enumerate(chunks)]
	processed_chunks = await asyncio.gather(*tasks)
	insert_tasks = [insert_chunk(chunk) for chunk in processed_chunks]
	await asyncio.gather(*insert_tasks)

async def crawl_parallel(urls: List[str], max_concurrent: int = 5):
	"""Crawl multiple URLs in parallel with a concurrency limit."""
	browser_config = BrowserConfig(
		headless=True,
		verbose=False,
		extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
	)
	crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

	crawler = AsyncWebCrawler(config=browser_config)
	await crawler.start()

	try:
		semaphore = asyncio.Semaphore(max_concurrent)
		
		async def process_url(url: str):
			async with semaphore:
				result = await crawler.arun(
					url=url,
					config=crawl_config,
					session_id="session1"
				)
				if result.success:
					print(f"Successfully crawled: {url}")
					await process_and_store_document(url, result.markdown_v2.raw_markdown)
				else:
					print(f"Failed: {url} - Error: {result.error_message}")
		
		await asyncio.gather(*[process_url(url) for url in urls])
	finally:
		await crawler.close()

def get_ultravox_docs_urls() -> List[str]:
	"""Get URLs from Ultravox documentation."""
	base_url = "https://docs.ultravox.ai"
	urls = set()
	
	try:
		# Start with the introduction page
		response = requests.get(f"{base_url}/introduction")
		response.raise_for_status()
		
		soup = BeautifulSoup(response.text, 'html.parser')
		
		# Find all links in the navigation/sidebar
		for link in soup.find_all('a'):
			href = link.get('href')
			if href and href.startswith('/'):
				full_url = urljoin(base_url, href)
				urls.add(full_url)
		
		return list(urls)
	except Exception as e:
		print(f"Error fetching URLs: {e}")
		return []

async def main():
	# Get URLs from Ultravox docs
	urls = get_ultravox_docs_urls()
	if not urls:
		print("No URLs found to crawl")
		return
	
	print(f"Found {len(urls)} URLs to crawl")
	await crawl_parallel(urls)

if __name__ == "__main__":
	asyncio.run(main())