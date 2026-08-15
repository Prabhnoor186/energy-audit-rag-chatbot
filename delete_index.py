"""delete_index.py — removes the existing (incorrectly-typed) index so we can start fresh."""
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

COLLECTION_ENDPOINT = "orwbrix3dyknur9wqbcd.eu-north-1.aoss.amazonaws.com"
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "aoss")

client = OpenSearch(
    hosts=[{"host": COLLECTION_ENDPOINT, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=60,
    max_retries=3,
    retry_on_timeout=True,
)

if client.indices.exists(index=INDEX_NAME):
    client.indices.delete(index=INDEX_NAME)
    print(f"Deleted index '{INDEX_NAME}'.")
else:
    print(f"Index '{INDEX_NAME}' doesn't exist — nothing to delete.")
