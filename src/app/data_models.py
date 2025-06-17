from typing import Optional
from datetime import datetime

from strenum import StrEnum
from pydantic import BaseModel, Field


class User(StrEnum):
    MANAGER = "Person 1"
    SUPERVISOR = "Person 2"
    DOCTOR = "Person 3"
    OTHER = "Other"


class DatabaseRecord(BaseModel):
    """
    Base class for all database records
    """
    date: datetime = Field(description="Date time of the record", default=datetime.now())
    updated_by: User = Field(description="Last updated by")


class Patient(BaseModel):
    name: str = Field(description="Name of the patient")
    phone: str = Field(description="Phone number of the patient", default=None)
    address: str = Field(description="Address of the patient", default=None)


class Doctor(BaseModel):
    name: str = Field(description="Name of the doctor")
    location: str = Field(description="location of the doctor", default=None)
    phone: str = Field(description="Phone number of the doctor", default=None)
    

#TODO: prices do not change so this can be a simple lookup table
class MedicalTest(BaseModel):
    name: str = Field(description="Name of the test")
    price: int = Field(description="Price of the test", default=None)


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
    medical_test: MedicalTest = Field(description="Medical test performed on the patient")
    payment: Payment = Field(description="Payment made for the medical test")
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
        lines.append(f"Paid {self.payment.amount} Rupees for {self.medical_test.name}")
        if self.comments:
            lines.append(f"Comments: {self.comments}")
            
        return "<br>".join(lines)


class ExpenseType(StrEnum):
    DOCTOR_FEES = "Doctor Fees"
    STAFF_EXPENSE = "Staff Expense"
    EQUIPMENT = "Equipment"
    RENT = "Rent"
    SALARY = "Salary"
    STATIONARY = "Stationary"
    CHAI_NASHTA = "Chai Nashta"
    MISCELLANEOUS = "Miscellaneous"


class ExpenseRecord(DatabaseRecord):
    expense_type: ExpenseType = Field(description="Type of expense")
    amount: int = Field(description="Amount of the expense")
    description: str = Field(description="Description of the expense", default=None)


class LedgerRecord(DatabaseRecord):
    initiator: User = Field(description="User who initiated the payment")
    benefactor: User = Field(description="User who collected the payment")
    amount: int = Field(description="Amount of the payment")
    description: str = Field(description="Description of the payment", default=None)


class ReferralRecord(DatabaseRecord):
    doctor: Doctor = Field(description="Doctor who referred the patient")
    medical_test: MedicalTest = Field(description="Medical test that was referred", default=None)
    patient_amount: Payment = Field(description="Payment made by the patient", default=None)
    doctor_amount: Payment = Field(description="Referral amount charged by the doctor")
    comments: str = Field(description="Comments on the referral", default=None)


class DBCollectionNames(StrEnum):
    MEDICAL_RECORDS = "medical_records"
    EXPENSES = "expenses"
    LEDGER = "ledger"


if __name__=="__main__":

    CURRENT_USER = User.SUPERVISOR.value
    
    medical_entry = MedicalRecord(
        patient=Patient(name="John Doe"),
        doctor=Doctor(name="Dr. Smith", location="Bangalore"),
        medical_test=MedicalTest(name="Blood Test", price=200),
        payment=Payment(amount=200),
        comments="Test comments",
        updated_by=CURRENT_USER
    )
    print (medical_entry.model_dump(mode="json"))
