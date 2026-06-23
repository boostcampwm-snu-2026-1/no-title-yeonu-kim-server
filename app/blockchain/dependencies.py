from app.blockchain.service import BlockchainService
from app.blockchain.service_impl import BlockchainServiceImpl


def get_blockchain_service() -> BlockchainService:
    return BlockchainServiceImpl()
