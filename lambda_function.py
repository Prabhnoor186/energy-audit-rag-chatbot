

import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

COLLECTION_ENDPOINT = "xatt8fd5jbtwnwha516i.eu-north-1.aoss.amazonaws.com"
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
TEXT_MODEL_ID = "eu.amazon.nova-micro-v1:0"  


credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "aoss")

opensearch_client = OpenSearch(
    hosts=[{"host": COLLECTION_ENDPOINT, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
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


def search_chunks(question: str, top_k: int = 3):
    query_vector = embed_text(question)
    search_body = {
        "size": top_k,
        "query": {
            "knn": {
                "vector": {"vector": query_vector, "k": top_k}
            }
        }
    }
    response = opensearch_client.search(index=INDEX_NAME, body=search_body)
    return response["hits"]["hits"]


def generate_answer(question: str, chunks: list) -> str:
    """NEW step: build a prompt from the question + retrieved chunks,
    send it to Amazon Nova Micro, return the written answer.
    Nova uses a "messages" format (like a chat turn), different from Titan Text."""

    context_text = "\n\n".join(
        f"[Source: {c['_source']['source']} - {c['_source']['section']}]\n{c['_source']['chunk_text']}"
        for c in chunks
    )

    prompt = f"""You are an assistant answering questions about energy audit reports.
Use ONLY the context below to answer. If the answer isn't in the context,
say "I don't have information on that in the audit reports."

Context:
{context_text}

Question: {question}

Answer:"""

    response = bedrock.invoke_model(
        modelId=TEXT_MODEL_ID,
        body=json.dumps({
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "inferenceConfig": {
                "maxTokens": 400,
                "temperature": 0.2,   # low temperature = stick close to the context, less "creative" guessing
                "topP": 0.9
            }
        })
    )
    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"].strip()


def lambda_handler(event, context):
    try:
        # API Gateway sends the request body as a JSON string inside event["body"]
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "").strip()

        if not question:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "No question provided"})
            }

        chunks = search_chunks(question)
        answer = generate_answer(question, chunks)

        sources = [
            {
                "source": c["_source"]["source"],
                "section": c["_source"]["section"],
                "chunk_text": c["_source"]["chunk_text"],
                "score": round(c["_score"], 4)
            }
            for c in chunks
        ]

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"answer": answer, "sources": sources})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }