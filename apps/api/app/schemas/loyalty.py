from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LoyaltyProgramUpdate(BaseModel):
    minimum_purchase: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    stamps_per_purchase: int = Field(gt=0, le=20)
    reward_stamps: int = Field(gt=0, le=1000)


class LoyaltyQrIssueIn(BaseModel):
    purpose: Literal["visit", "redemption"] = "visit"
    reward_id: UUID | None = None

    @model_validator(mode="after")
    def reward_matches_purpose(self):
        if (self.purpose == "redemption") != (self.reward_id is not None):
            raise ValueError("Indica un premio solo para un QR de canje")
        return self


class LoyaltyQrOut(BaseModel):
    token: str
    purpose: Literal["visit", "redemption"]
    expires_at: str
    expires_in_seconds: int
    reward_name: str | None = None


class LoyaltyQrRedeemIn(BaseModel):
    token: str = Field(min_length=24, max_length=128)


class LoyaltyDemoPurchaseIn(BaseModel):
    token: str = Field(min_length=24, max_length=128)


class LoyaltyInsightRequest(BaseModel):
    explain_with_llm: bool = False
