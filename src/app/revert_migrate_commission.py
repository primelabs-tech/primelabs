"""
Revert tool to undo the margin-based commission migration.

Recalculates commissions using the OLD formula (test_cost = 0):
    commission = (original_price * rate%) - discount   [percentage]
    commission = fixed_rate - discount                  [fixed]
    commission = max(0, commission)

This is equivalent to the system before test costs were introduced.

Usage:
    cd src/app
    streamlit run revert_migrate_commission.py
"""

import streamlit as st
from datetime import datetime
import calendar
from data_models import (
    DBCollectionNames,
    CommissionType,
    TestCategory,
    IST,
)
from firestore_crud import FirestoreCRUD

db = FirestoreCRUD()


# ─── HELPERS ────────────────────────────────────────────────────────────────────

def get_test_category(test_name: str, test_price: int) -> TestCategory:
    test_name_upper = test_name.upper()

    if test_name_upper.startswith("CT-SCAN") or test_name_upper.startswith("CT SCAN"):
        return TestCategory.CT_SCAN

    if test_name_upper.startswith("X-RAY") or test_name_upper.startswith("XRAY"):
        if test_price <= 350:
            return TestCategory.XRAY_350
        elif test_price <= 450:
            return TestCategory.XRAY_450
        else:
            return TestCategory.XRAY_650

    if "USG" in test_name_upper or "ULTRASOUND" in test_name_upper or "SONOGRAPHY" in test_name_upper:
        if test_price <= 750:
            return TestCategory.USG_750
        else:
            return TestCategory.USG_1200

    if "ECG" in test_name_upper or "EKG" in test_name_upper:
        return TestCategory.ECG

    return TestCategory.PATH


def recalculate_old_referral_info(record: dict, doctor_data: dict) -> dict:
    """
    Recalculate referral_info using the OLD formula (test_cost = 0):
        commission = (original_price * rate%) - discount
        commission = max(0, commission)

    Retrieves original_price and discount from the existing referral_info's
    test_commissions when available; otherwise uses stored test price.
    """
    commission_rates = doctor_data.get('commission_rates', [])
    commission_lookup = {}
    for cr in commission_rates:
        cat = cr.get('category', '')
        commission_lookup[cat] = {
            'type': cr.get('commission_type', CommissionType.PERCENTAGE.value),
            'rate': cr.get('rate', 0)
        }

    existing_test_details = {}
    existing_ri = record.get('referral_info', {})
    if existing_ri and isinstance(existing_ri, dict):
        for tc in existing_ri.get('test_commissions', []):
            if isinstance(tc, dict):
                existing_test_details[tc.get('test_name', '')] = tc

    medical_tests = record.get('medical_tests', [])
    test_commission_details = []
    total_commission = 0

    for test in medical_tests:
        test_name = test.get('name', '')
        paid_price = test.get('price', 0) or 0

        existing_detail = existing_test_details.get(test_name, {})
        original_price = existing_detail.get('original_price', paid_price)
        discount = existing_detail.get('discount', 0)

        test_category = get_test_category(test_name, original_price)

        if test_category.value in commission_lookup:
            cr = commission_lookup[test_category.value]
            comm_type = cr['type']
            comm_rate = cr['rate']
        else:
            comm_type = CommissionType.PERCENTAGE.value
            comm_rate = 0

        # OLD formula: margin = original_price (no cost deducted)
        if comm_type == CommissionType.PERCENTAGE.value:
            commission_amount = int(original_price * comm_rate / 100)
        else:
            commission_amount = int(comm_rate)
        commission_amount = max(0, commission_amount - discount)

        total_commission += commission_amount

        test_commission_details.append({
            'test_name': test_name,
            'test_category': test_category.value,
            'original_price': original_price,
            'paid_price': paid_price,
            'discount': discount,
            'test_cost': 0,
            'commission_type': comm_type,
            'commission_rate': float(comm_rate),
            'commission_amount': commission_amount,
        })

    return {
        'doctor_id': doctor_data.get('doctor_id', doctor_data.get('id', '')),
        'doctor_name': doctor_data.get('name', ''),
        'doctor_location': doctor_data.get('location', ''),
        'test_commissions': test_commission_details,
        'total_commission': total_commission,
    }


# ─── STREAMLIT APP ──────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Revert Commission Migration",
        page_icon="⏪",
        layout="wide"
    )

    st.title("⏪ Revert Commission Migration")
    st.warning(
        "⚠️ **LOCAL USE ONLY** — This tool reverts commissions to the **old formula** (before test costs):\n\n"
        "`commission = (original_price × rate%) − discount`  (test_cost treated as 0)"
    )
    st.markdown("---")

    # Collection selection
    try:
        medical_collection = DBCollectionNames(st.secrets["database_collection"]).value
    except Exception:
        medical_collection = st.text_input(
            "Database Collection",
            value="medical_records",
            help="Firestore collection name for medical records"
        )

    st.caption(f"Using collection: `{medical_collection}`")

    # Date range selection
    st.subheader("📅 Select Month to Revert")
    col1, col2 = st.columns(2)

    with col1:
        now = datetime.now()
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox(
            "Month",
            options=month_names,
            index=now.month - 1,
            key="revert_month"
        )
        selected_month = month_names.index(selected_month_name) + 1

    with col2:
        current_year = now.year
        years = list(range(2024, current_year + 1))
        selected_year = st.selectbox(
            "Year",
            options=years,
            index=len(years) - 1,
            key="revert_year"
        )

    st.markdown("---")

    # Load registered doctors
    with st.spinner("Loading registered doctors..."):
        try:
            registered_doctors = db.get_docs(
                DBCollectionNames.REGISTERED_DOCTORS.value,
                limit=500
            )
            doctor_lookup = {}
            for doc in registered_doctors:
                doc_id = doc.get('doctor_id', doc.get('id', ''))
                if doc_id:
                    doctor_lookup[doc_id] = doc
            st.success(f"✅ Loaded {len(registered_doctors)} registered doctors")
        except Exception as e:
            st.error(f"Error loading doctors: {str(e)}")
            return

    # Scan button
    if st.button("🔍 Scan Records for Month", type="primary"):
        with st.spinner(f"Loading records for {selected_month_name} {selected_year}..."):
            try:
                records = db.get_docs_for_month(
                    collection=medical_collection,
                    year=selected_year,
                    month=selected_month,
                    date_field="date",
                    limit=10000
                )
                st.session_state.revert_commission_records = records
                st.success(f"✅ Loaded {len(records)} records")
            except Exception as e:
                st.error(f"Error loading records: {str(e)}")
                st.session_state.revert_commission_records = []

    # Process loaded records
    if 'revert_commission_records' not in st.session_state:
        return

    records = st.session_state.revert_commission_records
    if not records:
        st.info("No records found for this month.")
        return

    # Filter to records that have referral_info with a doctor_id
    referral_records = []
    for r in records:
        ri = r.get('referral_info')
        if ri and isinstance(ri, dict) and ri.get('doctor_id'):
            referral_records.append(r)

    st.markdown("---")
    st.subheader(f"📋 Records with Referral Info: {len(referral_records)} / {len(records)}")

    if not referral_records:
        st.info("No records with referral info to revert.")
        return

    # Calculate diffs
    revert_plan = []
    total_current_commission = 0
    total_reverted_commission = 0
    missing_doctors = set()

    for record in referral_records:
        record_id = record.get('id', '')
        referral_info = record.get('referral_info', {})
        doctor_id = referral_info.get('doctor_id', '')
        current_commission = referral_info.get('total_commission', 0)
        total_current_commission += current_commission

        doctor_data = doctor_lookup.get(doctor_id)
        if not doctor_data:
            missing_doctors.add(f"{referral_info.get('doctor_name', '?')} ({doctor_id})")
            total_reverted_commission += current_commission
            continue

        reverted_referral_info = recalculate_old_referral_info(record, doctor_data)
        reverted_commission = reverted_referral_info['total_commission']
        total_reverted_commission += reverted_commission

        diff = reverted_commission - current_commission
        revert_plan.append({
            'record_id': record_id,
            'patient_name': record.get('patient', {}).get('name', 'Unknown'),
            'doctor_name': referral_info.get('doctor_name', ''),
            'current_commission': current_commission,
            'reverted_commission': reverted_commission,
            'diff': diff,
            'reverted_referral_info': reverted_referral_info,
        })

    # Summary
    diff_total = total_reverted_commission - total_current_commission
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Total Commission", f"₹{total_current_commission:,}")
    with col2:
        st.metric("Reverted Total Commission", f"₹{total_reverted_commission:,}")
    with col3:
        delta_color = "inverse" if diff_total < 0 else "normal"
        st.metric("Difference", f"₹{diff_total:,}", delta=f"₹{diff_total:,}", delta_color=delta_color)

    if missing_doctors:
        st.warning(f"⚠️ {len(missing_doctors)} doctor(s) not found in registry (records skipped):")
        for md in missing_doctors:
            st.caption(f"  • {md}")

    st.markdown("---")

    # Show records with changes
    changed_records = [r for r in revert_plan if r['diff'] != 0]
    unchanged_records = [r for r in revert_plan if r['diff'] == 0]

    st.subheader(f"🔄 Records with Commission Changes: {len(changed_records)}")

    if not changed_records:
        st.success("All records already match the old formula. Nothing to revert.")
        return

    with st.expander(f"📊 View all {len(changed_records)} changes", expanded=True):
        for i, item in enumerate(changed_records, 1):
            diff_str = f"+₹{item['diff']:,}" if item['diff'] > 0 else f"-₹{abs(item['diff']):,}"
            diff_color = "#dc3545" if item['diff'] < 0 else "#28a745"
            st.markdown(
                f"{i}. **{item['patient_name']}** (Dr. {item['doctor_name']}) — "
                f"₹{item['current_commission']:,} → ₹{item['reverted_commission']:,} "
                f"(<span style='color:{diff_color}'>{diff_str}</span>)",
                unsafe_allow_html=True
            )

    if unchanged_records:
        st.caption(f"ℹ️ {len(unchanged_records)} record(s) unchanged (commission same with old formula).")

    st.markdown("---")

    # Apply revert
    st.subheader("⏪ Apply Revert")

    col1, col2 = st.columns(2)

    with col1:
        confirm = st.checkbox(
            f"I confirm I want to revert {len(changed_records)} records to the old formula",
            key="confirm_revert"
        )

    with col2:
        if confirm:
            if st.button("⏪ Revert Changes", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                success_count = 0
                error_count = 0

                for i, item in enumerate(changed_records):
                    try:
                        db.update_doc(
                            medical_collection,
                            item['record_id'],
                            {"referral_info": item['reverted_referral_info']}
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        st.error(f"Failed to revert {item['record_id']}: {str(e)}")

                    progress = (i + 1) / len(changed_records)
                    progress_bar.progress(progress)
                    status_text.text(f"Reverting {i + 1}/{len(changed_records)}...")

                status_text.empty()
                progress_bar.empty()

                if error_count == 0:
                    st.success(f"✅ Successfully reverted {success_count} records to old formula!")
                    st.balloons()
                else:
                    st.warning(f"Done: {success_count} reverted, {error_count} failed.")

                if 'revert_commission_records' in st.session_state:
                    del st.session_state.revert_commission_records
        else:
            st.info("☑️ Check the confirmation box to enable revert.")


if __name__ == "__main__":
    main()
