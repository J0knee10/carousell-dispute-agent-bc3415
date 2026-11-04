"""Photo checking (nice to have in the brief): interface only.

Cases currently carry text descriptions of photos, which the claim-matching
step already reads. A real implementation would send the listing photos and the
buyer's photos to a vision-capable model and return what differs. Nothing in
the graph calls it yet: adding it means implementing PhotoChecker and a graph
node that passes its findings to claim matching.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class PhotoFinding(BaseModel):
    matches_listing: bool | None
    differences: list[str]
    note: str


class PhotoChecker(Protocol):
    def compare(self, listing_photos: list[bytes], buyer_photos: list[bytes], listing_text: str) -> PhotoFinding: ...


class DisabledPhotoChecker:
    """Default: no vision model configured."""

    def compare(self, listing_photos: list[bytes], buyer_photos: list[bytes], listing_text: str) -> PhotoFinding:
        return PhotoFinding(
            matches_listing=None,
            differences=[],
            note="Photo checking is not enabled. The agent uses the text descriptions of photos instead.",
        )
