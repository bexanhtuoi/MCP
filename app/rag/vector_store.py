from app.rag.embedding import get_embedding_model
from langchain_community.vectorstores import TiDBVectorStore
import os 

tidb_prefix = os.environ["TIDB_PREFIX"]
tidb_password = os.environ["TIDB_PASSWORD"]
tidb_host = os.environ["TIDB_HOST"]
tidb_port = os.environ["TIDB_PORT"]
tidb_db = os.environ["TIDB_DB"]
# ca_path = os.environ["TIDB_SSL_CA_PATH"]

DATABASE_URL = (
    f"mysql+pymysql://{tidb_prefix}:{tidb_password}"
    f"@{tidb_host}:{tidb_port}/{tidb_db}"
    f"?ssl_verify_cert=true&ssl_verify_identity=true"
)

embed_model = get_embedding_model()

def init_vector_store() -> TiDBVectorStore:
    client = TiDBVectorStore(
        table_name='embedded_documents',
        connection_string=DATABASE_URL,
        embedding_function=embed_model,
        # drop_existing_table=True, # chỉ dùng khi cần khởi tạo lại bảng
        engine_args={
        "pool_pre_ping": True,
        "pool_recycle": 300,  
    })
    return client   



