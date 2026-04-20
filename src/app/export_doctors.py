"""
Export Doctors Tool

Streamlit page that reads all registered doctors from Firestore
and allows exporting them to a CSV file.
"""

import streamlit as st
import csv
import io
from datetime import datetime, timezone, timedelta
from firestore_crud import FirestoreCRUD
from data_models import DBCollectionNames, TestCategory
from utils import get_firestore, format_datetime_for_display

ALL_TEST_CATEGORIES = list(TestCategory)


IST = timezone(timedelta(hours=5, minutes=30))


@st.cache_data(ttl=300)
def get_all_doctors():
    """Fetch all registered doctors (cached)."""
    db = get_firestore()
    return db.get_docs(
        DBCollectionNames.REGISTERED_DOCTORS.value,
        limit=5000,
    )


def _rates_by_category(rates: list[dict]) -> dict[str, str]:
    """Index commission rates by category value for quick lookup."""
    lookup = {}
    for r in rates:
        cat = r.get("category", "")
        rate = r.get("rate", "")
        ctype = r.get("commission_type", "")
        lookup[cat] = f"{rate} ({ctype})" if rate else ""
    return lookup


def build_csv(doctors: list[dict]) -> str:
    """Build CSV string from a list of doctor dicts.

    Each TestCategory gets its own column so rates are easy to compare
    across doctors in a spreadsheet.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    test_headers = [cat.value for cat in ALL_TEST_CATEGORIES]

    writer.writerow([
        "Doctor ID",
        "Name",
        "Location",
        "Phone",
        "Active",
        *test_headers,
        "Created At",
        "Created By",
        "Notes",
    ])

    for doc in doctors:
        rates_lookup = _rates_by_category(doc.get("commission_rates", []))

        created_at = doc.get("created_at")
        if created_at:
            date_str, time_str = format_datetime_for_display(created_at)
            created_at_str = f"{date_str} {time_str}"
        else:
            created_at_str = ""

        writer.writerow([
            doc.get("doctor_id", ""),
            doc.get("name", ""),
            doc.get("location", ""),
            doc.get("phone", ""),
            "Yes" if doc.get("is_active", True) else "No",
            *[rates_lookup.get(cat.value, "") for cat in ALL_TEST_CATEGORIES],
            created_at_str,
            doc.get("created_by_email", ""),
            doc.get("notes", "") or "",
        ])

    return output.getvalue()


def main():
    st.set_page_config(
        page_title="Export Doctors",
        page_icon="📋",
        layout="wide",
    )

    st.markdown("""
    <style>
        .stats-card {
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .stats-number {
            font-size: 2.5em;
            font-weight: 700;
            color: #e94560;
        }
        .stats-label {
            color: #888;
            font-size: 0.9em;
        }
        div[data-testid="stExpander"] {
            background: #1a1a2e;
            border-radius: 8px;
            border: 1px solid #333;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("# 📋 Export Registered Doctors")
    st.markdown("*View all registered doctors and export to CSV*")
    st.markdown("---")

    with st.spinner("Loading doctors..."):
        try:
            doctors = get_all_doctors()
        except Exception as e:
            st.error(f"Failed to load doctors: {e}")
            return

    if not doctors:
        st.warning("No registered doctors found in the database.")
        return

    active = [d for d in doctors if d.get("is_active", True)]
    inactive = [d for d in doctors if not d.get("is_active", True)]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{len(doctors)}</div>
            <div class="stats-label">Total Doctors</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{len(active)}</div>
            <div class="stats-label">Active</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{len(inactive)}</div>
            <div class="stats-label">Inactive</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Filters ---
    with st.sidebar:
        st.markdown("### Filters")
        status_filter = st.radio(
            "Status",
            ["All", "Active Only", "Inactive Only"],
            index=0,
        )

    if status_filter == "Active Only":
        filtered = active
    elif status_filter == "Inactive Only":
        filtered = inactive
    else:
        filtered = doctors

    filtered = sorted(filtered, key=lambda d: d.get("name", "").lower())

    st.markdown(f"### Doctors ({len(filtered)})")

    for doc in filtered:
        name = doc.get("name", "Unknown")
        location = doc.get("location", "")
        phone = doc.get("phone", "") or "N/A"
        is_active = doc.get("is_active", True)
        status_badge = "🟢 Active" if is_active else "🔴 Inactive"

        with st.expander(f"Dr. {name} — {location}  ({status_badge})"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Doctor ID:** {doc.get('doctor_id', 'N/A')}")
                st.markdown(f"**Phone:** {phone}")
                st.markdown(f"**Status:** {status_badge}")
            with c2:
                created_at = doc.get("created_at")
                if created_at:
                    d_str, t_str = format_datetime_for_display(created_at)
                    st.markdown(f"**Registered:** {d_str} {t_str}")
                st.markdown(
                    f"**Created By:** {doc.get('created_by_email', 'N/A')}"
                )
                if doc.get("notes"):
                    st.markdown(f"**Notes:** {doc['notes']}")

            rates = doc.get("commission_rates", [])
            if rates:
                st.markdown("**Commission Rates:**")
                for r in rates:
                    st.markdown(
                        f"- {r.get('category', '?')}: "
                        f"{r.get('rate', 0)} ({r.get('commission_type', '')})"
                    )

    # --- Export ---
    st.markdown("---")
    st.markdown("### Export to CSV")

    csv_data = build_csv(filtered)
    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")

    st.download_button(
        label=f"Download CSV ({len(filtered)} doctors)",
        data=csv_data,
        file_name=f"doctors_export_{timestamp}.csv",
        mime="text/csv",
        type="primary",
    )


if __name__ == "__main__":
    main()
