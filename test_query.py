"""
test_query.py

Sanity check before building the full chatbot: take one sample question,
embed it (same way we embedded chunks), and search OpenSearch for the
closest-matching chunks. If this returns sensible results, your data
layer is confirmed working end-to-end.
"""

import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

COLLECTION_ENDPOINT = "orwbrix3dyknur9wqbcd.eu-north-1.aoss.amazonaws.com"
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"
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

bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def embed_text(text: str) -> list[float]:
    response = bedrock.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def search(question: str, top_k: int = 3):
    query_vector = embed_text(question)

    # k-NN search: "find the top_k stored vectors closest to this one"
    search_body = {
        "size": top_k,
        "query": {
            "knn": {
                "vector": {
                    "vector": query_vector,
                    "k": top_k
                }
            }
        }
    }

    response = client.search(index=INDEX_NAME, body=search_body)
    return response["hits"]["hits"]


if __name__ == "__main__":
    test_question = input("Ask a question about your audit reports: ")
    results = search(test_question)

    print(f"Question: {test_question}\n")
    print(f"Top {len(results)} matches:\n")
    for i, hit in enumerate(results, start=1):
        source = hit["_source"]
        score = hit["_score"]
        print(f"--- Match {i} (score: {score:.4f}) ---")
        print(f"From: {source['source']} — {source['section']}")
        print(source["chunk_text"][:300])
        print()
