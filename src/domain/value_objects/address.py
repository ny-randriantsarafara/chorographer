"""Address value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Address:
    """Immutable address from OSM addr:* tags."""

    street: str | None = None
    housenumber: str | None = None
    city: str | None = None
    postcode: str | None = None
    district: str | None = None
    province: str | None = None

    @property
    def is_empty(self) -> bool:
        """Check if address has any data."""
        return all(
            v is None
            for v in (
                self.street,
                self.housenumber,
                self.city,
                self.postcode,
                self.district,
                self.province,
            )
        )

    def format(self) -> str:
        """Format address as single line string."""
        parts: list[str] = []

        if self.housenumber and self.street:
            parts.append(f"{self.housenumber} {self.street}")
        elif self.street:
            parts.append(self.street)

        if self.district:
            parts.append(self.district)
        if self.city:
            parts.append(self.city)
        if self.province:
            parts.append(self.province)
        if self.postcode:
            parts.append(self.postcode)

        return ", ".join(parts)

    @classmethod
    def from_osm_tags(cls, tags: dict[str, str]) -> "Address":
        """Create Address from OSM tags dict."""
        return cls(
            street=tags.get("addr:street"),
            housenumber=tags.get("addr:housenumber"),
            city=tags.get("addr:city"),
            postcode=tags.get("addr:postcode"),
            district=tags.get("addr:district"),
            province=tags.get("addr:province"),
        )
