from typing import Optional, List
from datetime import datetime, timezone, timedelta

from strenum import StrEnum
from pydantic import BaseModel, Field


# Indian Standard Time offset (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now() -> datetime:
    """Get current datetime in Indian Standard Time (IST, UTC+5:30)"""
    return datetime.now(IST)


class UserRole(StrEnum):
    """User roles"""
    ADMIN = "Admin"
    MANAGER = "Manager"
    SUPERVISOR = "Supervisor"
    DOCTOR = "Doctor"
    EMPLOYEE = "Employee"


class AuthorizationStatus(StrEnum):
    """Authorization status"""
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    UNAUTHENTICATED = "Unauthenticated"
    UNAUTHORIZED = "Unauthorized"
    OWNER = "Owner"
    NON_OWNER = "Non-Owner"

class DatabaseRecord(BaseModel):
    """
    Base class for all database records
    """
    date: datetime = Field(description="Date time of the record (IST)", default_factory=get_ist_now)
    updated_by: UserRole = Field(description="Last updated by")
    updated_by_email: str = Field(description="Email of the user who last updated the record")


class Patient(BaseModel):
    name: str = Field(description="Name of the patient")
    phone: str = Field(description="Phone number of the patient", default=None)
    address: str = Field(description="Address of the patient", default=None)


class Doctor(BaseModel):
    name: str = Field(description="Name of the doctor")
    location: str = Field(description="location of the doctor", default=None)
    phone: str = Field(description="Phone number of the doctor", default=None)
    

class MedicalTest(BaseModel):
    name: str = Field(description="Name of the test")
    price: int = Field(description="Price paid for the test (after discount)", default=None)


class DoctorReferral(BaseModel):
    doctor: Doctor
    medical_test: MedicalTest
    amount: int = Field(description="Referral amount charged by the doctor")


class Payment(BaseModel):
    amount: int = Field(description="Amount of the payment")
    description: str = Field(description="Description of the payment", default=None)


class MedicalRecord(DatabaseRecord):
    patient: Patient = Field(description="Patient who underwent the medical test")
    doctor: Optional[Doctor] = Field(description="Doctor who referred the patient (legacy field)", default=None)
    referral_info: Optional["DoctorReferralInfo"] = Field(description="Referral info from registered doctor", default=None)
    medical_tests: List[MedicalTest] = Field(description="Medical tests performed on the patient")
    payment: Payment = Field(description="Payment made for the medical tests")
    comments : str = Field(description="Comments on the medical entry", default=None)
    
    def __str__(self) -> str:
        lines = [
            "Form submitted",
            f"Patient Name: {self.patient.name}"
        ]
        
        if self.patient.phone:
            lines.append(f"Patient Phone: {self.patient.phone}")
        if self.patient.address:
            lines.append(f"Patient Address: {self.patient.address}")
        if self.doctor:
            lines.append(f"Referred by Dr. {self.doctor.name} from {self.doctor.location}")
        
        # Handle multiple tests
        test_names = ", ".join([t.name for t in self.medical_tests])
        total_price = sum([t.price or 0 for t in self.medical_tests])
        lines.append(f"Paid {self.payment.amount} Rupees for {test_names} (Total price: {total_price})")
        
        if self.comments:
            lines.append(f"Comments: {self.comments}")
            
        return "<br>".join(lines)


class ExpenseType(StrEnum): 
    CHAI_NASHTA = "Chai Nashta"
    PETROL_DIESEL = "Petrol/Diesel"
    RENT = "Rent"
    ELECTRICITY = "Electricity"
    INTERNET = "Internet"
    STAFF_SALARY = "Staff Salary"
    DOCTOR_CUT = "Doctor Cut"
    DOCTOR_FEES = "Doctor Fees"
    MACHINE_REPAIR = "Machine Repair"
    MACHINE_INSTALL = "Machine Install"
    MACHINE_COST = "Machine Cost"
    PAPER_STATIONARY = "Paper/Stationary"
    THYROCARE = "Thyrocare"
    STAFF_EXPENSE = "Staff Kharcha"
    SALARY = "Salary"
    OTHER = "Other Expense"


EXPENSE_DESCRIPTIONS = {
    ExpenseType.CHAI_NASHTA: "Tea, snacks and refreshments",
    ExpenseType.PETROL_DIESEL: "Fuel expenses",
    ExpenseType.RENT: "Monthly office/clinic rent payments",
    ExpenseType.ELECTRICITY: "Electricity and utility bills",
    ExpenseType.INTERNET: "Internet and communication expenses",
    ExpenseType.STAFF_SALARY: "Staff salary payments",
    ExpenseType.DOCTOR_CUT: "Doctor referral cut payments",
    ExpenseType.DOCTOR_FEES: "Doctor consultation and professional fees",
    ExpenseType.MACHINE_REPAIR: "Machine repair costs",
    ExpenseType.MACHINE_INSTALL: "Machine installation costs",
    ExpenseType.MACHINE_COST: "Cost of buying a new machine",
    ExpenseType.PAPER_STATIONARY: "Office supplies and stationery",
    ExpenseType.THYROCARE: "Thyrocare related expenses",
    ExpenseType.STAFF_EXPENSE: "Staff-related expenses (excluding salary)",
    ExpenseType.SALARY: "Staff salary payments",
    ExpenseType.OTHER: "Other miscellaneous expenses",
}


class ExpenseRecord(DatabaseRecord):
    expense_type: ExpenseType = Field(description="Type of expense")
    amount: int = Field(description="Amount of the expense")
    description: str = Field(description="Description of the expense", default=None)


class LedgerRecord(DatabaseRecord):
    initiator: UserRole = Field(description="User who initiated the payment")
    benefactor: UserRole = Field(description="User who collected the payment")
    amount: int = Field(description="Amount of the payment")
    description: str = Field(description="Description of the payment", default=None)


class ReferralRecord(DatabaseRecord):
    doctor: Doctor = Field(description="Doctor who referred the patient")
    medical_test: MedicalTest = Field(description="Medical test that was referred", default=None)
    patient_amount: Payment = Field(description="Payment made by the patient", default=None)
    doctor_amount: Payment = Field(description="Referral amount charged by the doctor")
    comments: str = Field(description="Comments on the referral", default=None)


class CommissionType(StrEnum):
    """Commission calculation type"""
    PERCENTAGE = "Percentage"  # Commission is a percentage of test price
    FIXED = "Fixed"  # Fixed amount per test


class TestCategory(StrEnum):
    """
    Test categories for commission calculation.
    Based on the doctor commission sheet structure.
    """
    USG_750 = "USG-750"      # Ultrasound at ₹750
    USG_1200 = "USG-1200"    # Ultrasound at ₹1200
    XRAY_350 = "X-RAY-350"   # X-Ray at ₹350
    XRAY_450 = "X-RAY-450"   # X-Ray at ₹450
    XRAY_650 = "X-RAY-650"   # X-Ray at ₹650
    ECG = "ECG"              # ECG
    CT_SCAN = "CT-SCAN"      # CT Scan (usually percentage based)
    PATH = "PATH"            # Pathology/Blood tests (usually percentage based)


# Default commission rates structure (can be customized per doctor)
DEFAULT_COMMISSION_RATES = {
    TestCategory.USG_750: {"type": CommissionType.FIXED, "rate": 250},
    TestCategory.USG_1200: {"type": CommissionType.FIXED, "rate": 300},
    TestCategory.XRAY_350: {"type": CommissionType.FIXED, "rate": 100},
    TestCategory.XRAY_450: {"type": CommissionType.FIXED, "rate": 100},
    TestCategory.XRAY_650: {"type": CommissionType.FIXED, "rate": 150},
    TestCategory.ECG: {"type": CommissionType.FIXED, "rate": 100},
    TestCategory.CT_SCAN: {"type": CommissionType.PERCENTAGE, "rate": 40},
    TestCategory.PATH: {"type": CommissionType.PERCENTAGE, "rate": 50},
}


class TestCommissionRate(BaseModel):
    """Commission rate for a specific test category"""
    category: TestCategory = Field(description="Test category")
    commission_type: CommissionType = Field(description="Percentage or Fixed")
    rate: float = Field(description="Rate value (% or fixed amount in rupees)")
    
    def calculate_commission(self, test_price: int) -> int:
        """Calculate commission for this test"""
        if self.commission_type == CommissionType.PERCENTAGE:
            return int(test_price * self.rate / 100)
        else:  # Fixed
            return int(self.rate)


class RegisteredDoctor(BaseModel):
    """
    Registered doctor in the system - ONLY Admin can create/modify.
    This prevents fraud by locking commission rates at the admin level.
    
    Each doctor has commission rates for each test category.
    """
    doctor_id: str = Field(description="Unique identifier for the doctor")
    name: str = Field(description="Full name of the doctor")
    location: str = Field(description="Clinic/Hospital location")
    phone: Optional[str] = Field(description="Phone number", default=None)
    
    # Commission rates by test category
    commission_rates: List[TestCommissionRate] = Field(
        description="Commission rates for each test category",
        default_factory=list
    )
    
    is_active: bool = Field(description="Whether the doctor is currently active", default=True)
    created_at: datetime = Field(description="When the doctor was registered", default_factory=get_ist_now)
    created_by_email: str = Field(description="Admin who registered this doctor")
    notes: Optional[str] = Field(description="Admin notes about this doctor", default=None)
    
    def get_commission_for_category(self, category: TestCategory, test_price: int) -> tuple:
        """
        Get commission for a specific test category.
        Returns (commission_amount, commission_type, rate)
        """
        for cr in self.commission_rates:
            if cr.category == category:
                return (cr.calculate_commission(test_price), cr.commission_type, cr.rate)
        
        # Fallback to default if category not found
        default = DEFAULT_COMMISSION_RATES.get(category, {"type": CommissionType.PERCENTAGE, "rate": 0})
        if default["type"] == CommissionType.PERCENTAGE:
            commission = int(test_price * default["rate"] / 100)
        else:
            commission = int(default["rate"])
        return (commission, default["type"], default["rate"])


class TestCommissionDetail(BaseModel):
    """Detail of commission for a single test in a referral"""
    test_name: str = Field(description="Name of the test")
    test_category: TestCategory = Field(description="Category of the test")
    test_price: int = Field(description="Price paid for the test")
    commission_type: CommissionType = Field(description="Commission type used")
    commission_rate: float = Field(description="Commission rate used")
    commission_amount: int = Field(description="Calculated commission amount")


class DoctorReferralInfo(BaseModel):
    """
    Referral information stored with medical record.
    Links to a registered doctor and stores commission breakdown by test.
    """
    doctor_id: str = Field(description="ID of the registered doctor")
    doctor_name: str = Field(description="Name of the doctor (denormalized for display)")
    doctor_location: str = Field(description="Location of the doctor (denormalized for display)")
    
    # Commission breakdown by test
    test_commissions: List[TestCommissionDetail] = Field(
        description="Commission details for each test",
        default_factory=list
    )
    
    # Total commission (sum of all test commissions)
    total_commission: int = Field(description="Total commission amount for all tests")


class DBCollectionNames(StrEnum):
    MEDICAL_RECORDS_PROD = "medical_records"
    MEDICAL_RECORDS_DEV = "medical_records_dev"
    EXPENSES_PROD = "expenses"
    EXPENSES_DEV = "expenses_dev"
    LEDGER_PROD = "ledger"
    LEDGER_DEV = "ledger_dev"
    REGISTERED_DOCTORS = "registered_doctors"  # Admin-managed doctor registry


if __name__=="__main__":

    CURRENT_USER = UserRole.SUPERVISOR.value
    
    medical_entry = MedicalRecord(
        patient=Patient(name="John Doe"),
        doctor=Doctor(name="Dr. Smith", location="Bangalore"),
        medical_tests=[
            MedicalTest(name="Blood Test", price=200),
            MedicalTest(name="Urine Test", price=150)
        ],
        payment=Payment(amount=350),
        comments="Test comments",
        updated_by=CURRENT_USER,
        updated_by_email="test@example.com"
    )
    print (medical_entry.model_dump(mode="json"))
