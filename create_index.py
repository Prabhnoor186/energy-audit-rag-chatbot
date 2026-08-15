
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

COLLECTION_ENDPOINT = "xatt8fd5jbtwnwha516i.eu-north-1.aoss.amazonaws.com"  
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"
VECTOR_DIM = 1024  

# ---- authenticate using your AWS CLI credentials (same ones aws configure set up) ----
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "aoss")  # "aoss" = the service name OpenSearch Serverless signs requests as

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

# ---- the index definition: field names + types ----
index_body = {
    "settings": {
        "index": {
            "knn": True 
        }
    },
    "mappings": {
        "properties": {
            "chunk_text": {"type": "text"},
            "source": {"type": "keyword"},
            "section": {"type": "keyword"},
            "vector": {
                "type": "knn_vector",
                "dimension": VECTOR_DIM,
                "method": {
                    "name": "hnsw",       
                    "engine": "faiss",
                    "space_type": "cosinesimil" 
                }
            }
        }
    }
}

if __name__ == "__main__":
    if client.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists — nothing to do.")
    else:
        response = client.indices.create(index=INDEX_NAME, body=index_body)
        print("Index created:", response)