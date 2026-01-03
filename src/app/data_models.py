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
    doctor: Optional[Doctor] = Field(description="Doctor who referred the patient", default=None)
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
    MACHINE_REPAIR = "Machine Repair"
    MACHINE_INSTALL = "Machine Install"
    STATIONARY = "Paper/Stationary"
    THYROCARE = "Thyrocare"
    STAFF_EXPENSE = "Staff Kharcha - add comment"    
    OTHER = "Other Expense - add comment"


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


class DBCollectionNames(StrEnum):
    MEDICAL_RECORDS_PROD = "medical_records"
    MEDICAL_RECORDS_DEV = "medical_records_dev"
    EXPENSES_PROD = "expenses"
    EXPENSES_DEV = "expenses_dev"
    LEDGER_PROD = "ledger"
    LEDGER_DEV = "ledger_dev"


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
