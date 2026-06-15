from pydantic import BaseModel


class DepositReq(BaseModel):
    amount: int


class DepositResp(BaseModel):
    balance: int
    depositedAt: str
