"""
crm_service.py
==============

Mock CRM (Customer Relationship Management) service API.

Provides a fully functional **in-memory** CRM for development, demo,
and testing — no external database or HTTP calls required.

Endpoints Simulated
-------------------
- ``GET  /crm/customer?mobile=``  — look up a customer by mobile number.
- ``POST /crm/lead``              — create a new lead record.
- ``PATCH /crm/lead/{lead_id}``   — update an existing lead record.
- ``GET  /crm/lead/{lead_id}``    — retrieve a lead by ID.
- ``GET  /crm/search?pan=``       — search by PAN number.

Dummy Dataset
-------------
Ships with 10 pre-seeded customer records across multiple cities,
KYC statuses, and customer flags.  Unknown mobiles trigger a
deterministic 'new customer' record generation.

Production Swap
---------------
Replace the class body with ``httpx.AsyncClient`` calls pointed at
your real CRM.  The interface (method signatures + return types)
remains identical so no consumer code needs to change.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CustomerRecord:
    """
    A customer record returned by the CRM.

    Attributes
    ----------
    customer_id : str
        Unique CRM identifier.
    name : str
        Full name of the customer.
    mobile : str
        10-digit Indian mobile number.
    email : str
        Email address.
    city : str
        City of residence.
    kyc_status : str
        One of ``verified``, ``pending``, ``expired``, ``not_started``.
    existing_customer : bool
        Whether this person already has a relationship with the lender.
    pan : str
        PAN number (masked in responses).
    credit_score : int
        Last known credit score (0 if not available).
    metadata : dict
        Arbitrary extra fields.
    """

    customer_id: str = ""
    name: str = ""
    mobile: str = ""
    email: str = ""
    city: str = ""
    kyc_status: str = "not_started"
    existing_customer: bool = False
    pan: str = ""
    credit_score: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-safe dictionary (masks PAN)."""
        masked_pan = f"XXXXXX{self.pan[-4:]}" if len(self.pan) >= 4 else self.pan
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "mobile": self.mobile,
            "email": self.email,
            "city": self.city,
            "kyc_status": self.kyc_status,
            "existing_customer": self.existing_customer,
            "pan": masked_pan,
            "credit_score": self.credit_score,
            "metadata": self.metadata,
        }


@dataclass
class LeadRecord:
    """
    Represents a lead / prospective borrower in the CRM.

    Attributes
    ----------
    lead_id : str
        Unique CRM identifier for the lead.
    name : str
        Full name of the applicant.
    mobile : str
        Primary mobile number.
    email : str
        Email address.
    loan_type : str
        Requested loan product category.
    status : str
        Current CRM pipeline status.
    metadata : dict
        Arbitrary additional fields.
    created_at : float
        Unix timestamp of creation.
    """

    lead_id: str = ""
    name: str = ""
    mobile: str = ""
    email: str = ""
    loan_type: str = ""
    status: str = "new"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "name": self.name,
            "mobile": self.mobile,
            "email": self.email,
            "loan_type": self.loan_type,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Dummy Customer Dataset (10 records)
# ═══════════════════════════════════════════════════════════════════════════

DUMMY_CUSTOMERS: List[CustomerRecord] = [
    CustomerRecord(
        customer_id="CUST-001",
        name="Rajesh Kumar",
        mobile="9876543210",
        email="rajesh.kumar@email.com",
        city="Mumbai",
        kyc_status="verified",
        existing_customer=True,
        pan="ABCPK1234A",
        credit_score=780,
        metadata={"segment": "premium", "relationship_years": 5},
    ),
    CustomerRecord(
        customer_id="CUST-002",
        name="Priya Sharma",
        mobile="9876543211",
        email="priya.sharma@email.com",
        city="Delhi",
        kyc_status="verified",
        existing_customer=True,
        pan="BCDPS5678B",
        credit_score=820,
        metadata={"segment": "premium", "relationship_years": 3},
    ),
    CustomerRecord(
        customer_id="CUST-003",
        name="Amit Patel",
        mobile="9876543212",
        email="amit.patel@email.com",
        city="Ahmedabad",
        kyc_status="pending",
        existing_customer=True,
        pan="CDEPA9012C",
        credit_score=720,
        metadata={"segment": "standard", "relationship_years": 1},
    ),
    CustomerRecord(
        customer_id="CUST-004",
        name="Sneha Reddy",
        mobile="9876543213",
        email="sneha.reddy@email.com",
        city="Hyderabad",
        kyc_status="expired",
        existing_customer=True,
        pan="DEFSR3456D",
        credit_score=690,
        metadata={"segment": "standard", "relationship_years": 2},
    ),
    CustomerRecord(
        customer_id="CUST-005",
        name="Vikram Singh",
        mobile="9876543214",
        email="vikram.singh@email.com",
        city="Chandigarh",
        kyc_status="verified",
        existing_customer=True,
        pan="EFGVS7890E",
        credit_score=750,
        metadata={"segment": "premium", "relationship_years": 7},
    ),
    CustomerRecord(
        customer_id="CUST-006",
        name="Ananya Gupta",
        mobile="8765432109",
        email="ananya.gupta@email.com",
        city="Kolkata",
        kyc_status="not_started",
        existing_customer=False,
        pan="FGHAG1234F",
        credit_score=0,
        metadata={"segment": "new", "source": "website"},
    ),
    CustomerRecord(
        customer_id="CUST-007",
        name="Rohit Mehta",
        mobile="8765432108",
        email="rohit.mehta@email.com",
        city="Pune",
        kyc_status="verified",
        existing_customer=True,
        pan="GHIRM5678G",
        credit_score=810,
        metadata={"segment": "premium", "relationship_years": 4},
    ),
    CustomerRecord(
        customer_id="CUST-008",
        name="Deepika Nair",
        mobile="7654321098",
        email="deepika.nair@email.com",
        city="Bengaluru",
        kyc_status="pending",
        existing_customer=False,
        pan="HIJDN9012H",
        credit_score=0,
        metadata={"segment": "new", "source": "referral"},
    ),
    CustomerRecord(
        customer_id="CUST-009",
        name="Suresh Iyer",
        mobile="7654321097",
        email="suresh.iyer@email.com",
        city="Chennai",
        kyc_status="verified",
        existing_customer=True,
        pan="IJKSI3456I",
        credit_score=770,
        metadata={"segment": "standard", "relationship_years": 2},
    ),
    CustomerRecord(
        customer_id="CUST-010",
        name="Kavita Joshi",
        mobile="6543210987",
        email="kavita.joshi@email.com",
        city="Jaipur",
        kyc_status="not_started",
        existing_customer=False,
        pan="JKLKJ7890J",
        credit_score=0,
        metadata={"segment": "new", "source": "branch_walk_in"},
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# CRM Service (Mock Implementation)
# ═══════════════════════════════════════════════════════════════════════════

class CRMService:
    """
    Mock CRM service with an in-memory dataset.

    Simulates:
    - ``GET  /crm/customer?mobile=``  → :meth:`get_customer_by_mobile`
    - ``POST /crm/lead``              → :meth:`create_lead`
    - ``PATCH /crm/lead/{id}``        → :meth:`update_lead`
    - ``GET  /crm/lead/{id}``         → :meth:`get_lead`
    - ``GET  /crm/search?pan=``       → :meth:`search_by_pan`

    Usage::

        crm = CRMService()
        customer = await crm.get_customer_by_mobile("9876543210")
        print(customer.to_dict())
    """

    def __init__(self) -> None:
        # Index customers by mobile for O(1) lookup
        self._customer_index: Dict[str, CustomerRecord] = {
            c.mobile: c for c in DUMMY_CUSTOMERS
        }
        # Index customers by PAN
        self._pan_index: Dict[str, CustomerRecord] = {
            c.pan: c for c in DUMMY_CUSTOMERS if c.pan
        }
        # Lead storage
        self._leads: Dict[str, LeadRecord] = {}
        self._lead_counter: int = 0

    # ──────────────────────────────────────────────────────────────────
    # GET /crm/customer?mobile=
    # ──────────────────────────────────────────────────────────────────

    async def get_customer_by_mobile(self, mobile: str) -> CustomerRecord:
        """
        Look up a customer by mobile number.

        **Simulates:** ``GET /crm/customer?mobile={mobile}``

        Parameters
        ----------
        mobile : str
            10-digit Indian mobile number.

        Returns
        -------
        CustomerRecord
            Matching record from the dataset, or a dynamically generated
            'new customer' record for unknown numbers.
        """
        clean = mobile.strip().replace("+91", "").replace(" ", "").replace("-", "")
        logger.info("CRM lookup by mobile=%s", clean)

        if clean in self._customer_index:
            record = self._customer_index[clean]
            logger.info("CRM hit: customer_id=%s name=%s", record.customer_id, record.name)
            return record

        # Unknown mobile → generate a deterministic 'new customer' record
        logger.info("CRM miss: mobile=%s → generating new customer record", clean)
        return self._generate_new_customer(clean)

    # ──────────────────────────────────────────────────────────────────
    # GET /crm/search?pan=
    # ──────────────────────────────────────────────────────────────────

    async def search_by_pan(self, pan: str) -> Optional[CustomerRecord]:
        """
        Search for an existing customer by PAN number.

        **Simulates:** ``GET /crm/search?pan={pan}``

        Returns ``None`` if no match is found.
        """
        pan = pan.strip().upper()
        logger.info("CRM search by PAN=%s", pan)
        return self._pan_index.get(pan)

    # ──────────────────────────────────────────────────────────────────
    # POST /crm/lead
    # ──────────────────────────────────────────────────────────────────

    async def create_lead(
        self,
        name: str,
        mobile: str,
        loan_type: str,
        email: str = "",
        **kwargs: Any,
    ) -> LeadRecord:
        """
        Create a new lead in the CRM.

        **Simulates:** ``POST /crm/lead``
        """
        self._lead_counter += 1
        lead_id = f"LEAD-{self._lead_counter:04d}"
        lead = LeadRecord(
            lead_id=lead_id,
            name=name,
            mobile=mobile,
            email=email,
            loan_type=loan_type,
            status="new",
            metadata=kwargs,
            created_at=time.time(),
        )
        self._leads[lead_id] = lead
        logger.info("CRM lead created: lead_id=%s name=%s loan_type=%s", lead_id, name, loan_type)
        return lead

    # ──────────────────────────────────────────────────────────────────
    # PATCH /crm/lead/{lead_id}
    # ──────────────────────────────────────────────────────────────────

    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> LeadRecord:
        """
        Update fields on an existing lead record.

        **Simulates:** ``PATCH /crm/lead/{lead_id}``
        """
        lead = self._leads.get(lead_id)
        if lead is None:
            logger.warning("CRM update for unknown lead_id=%s", lead_id)
            return LeadRecord(lead_id=lead_id)

        for key, value in updates.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
            else:
                lead.metadata[key] = value

        logger.info("CRM lead updated: lead_id=%s fields=%s", lead_id, list(updates.keys()))
        return lead

    # ──────────────────────────────────────────────────────────────────
    # GET /crm/lead/{lead_id}
    # ──────────────────────────────────────────────────────────────────

    async def get_lead(self, lead_id: str) -> Optional[LeadRecord]:
        """
        Retrieve a lead record by ID.

        **Simulates:** ``GET /crm/lead/{lead_id}``
        """
        logger.info("CRM get lead_id=%s", lead_id)
        return self._leads.get(lead_id)

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_new_customer(mobile: str) -> CustomerRecord:
        """
        Generate a deterministic 'new customer' record for an unknown mobile.

        Uses hash-based seeding to produce consistent fields across calls.
        """
        seed = hashlib.sha256(f"crm:{mobile}".encode()).hexdigest()
        cust_id = f"NEW-{seed[:6].upper()}"

        # Deterministic city assignment
        cities = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune",
                  "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
        city = cities[int(seed[:4], 16) % len(cities)]

        return CustomerRecord(
            customer_id=cust_id,
            name="",  # Unknown — to be captured during the flow
            mobile=mobile,
            email="",
            city=city,
            kyc_status="not_started",
            existing_customer=False,
            pan="",
            credit_score=0,
            metadata={"source": "chatbot", "auto_generated": True},
        )

    # ──────────────────────────────────────────────────────────────────
    # Bulk / Admin
    # ──────────────────────────────────────────────────────────────────

    async def list_customers(self) -> List[CustomerRecord]:
        """Return all customers in the dataset (for admin/debug)."""
        return list(self._customer_index.values())

    async def list_leads(self) -> List[LeadRecord]:
        """Return all leads (for admin/debug)."""
        return list(self._leads.values())

    @property
    def customer_count(self) -> int:
        return len(self._customer_index)

    @property
    def lead_count(self) -> int:
        return len(self._leads)
