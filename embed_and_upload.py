

import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


COLLECTION_ENDPOINT = "xatt8fd5jbtwnwha516i.eu-north-1.aoss.amazonaws.com"
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"
CHUNKS_FILE = "chunks.json"
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"


credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "aoss")

client = OpenSearch(
    hosts=[{"host": COLLECTION_ENDPOINT, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    pool_maxsize=20,
    timeout=60,           
    max_retries=3,        
    retry_on_timeout=True,
)

# ---- connect to Bedrock (separate service, separate client) ----
bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def embed_text(text: str) -> list[float]:
    """Send one piece of text to Titan Embeddings, get back its vector."""
    response = bedrock.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]  # a list of 1024 numbers


def main():
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Embedding and uploading {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks, start=1):
        vector = embed_text(chunk["text"])

        document = {
            "chunk_text": chunk["text"],
            "source": chunk["source"],
            "section": chunk["section"],
            "vector": vector,
        }

        client.index(index=INDEX_NAME, body=document)

        print(f"[{i}/{len(chunks)}] uploaded: {chunk['source']} — {chunk['section']}")

    print("Done. All chunks embedded and stored in OpenSearch.")


if __name__ == "__main__":
    main()