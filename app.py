"""
DC Audit Report Generator v2.0
Physical audit sheet generator with PDF export for inventory verification

CHANGELOG:
v2.0 (2025-11-07)
- Redesigned with "Report Builder" workflow
- Added PDF generation for physical audits
- Moved filters to main content area
- Added audit-friendly formatting with checkboxes
- Signature lines and audit metadata

v1.0 (2025-11-07)
- Initial release
"""

import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Page config
st.set_page_config(
    page_title="DC Audit Report v2.0",
    page_icon="📋",
    layout="wide"
)

# Version and constants
VERSION = "2.0"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_brand_from_product(product_name):
    """
    Extract brand from product name (everything before ' - ')
    
    Args:
        product_name (str): Full product name like "Pretty Dope - 24k Gold Vape 1g"
        
    Returns:
        str: Brand name or 'Unknown' if not found
    """
    if pd.isna(product_name):
        return 'Unknown'
    
    name_str = str(product_name).strip()
    if ' - ' in name_str:
        brand = name_str.split(' - ')[0].strip()
        return brand if brand else 'Unknown'
    else:
        return 'Unknown'

def safe_numeric(value, default=0):
    """Safely convert value to numeric, return default if fails"""
    try:
        return float(value) if pd.notna(value) else default
    except:
        return default

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_packages_csv(uploaded_file):
    """
    Load packages CSV file
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        DataFrame or None if error
    """
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return None

# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================

def validate_required_columns(df):
    """Validate that DataFrame has required columns for audit processing"""
    if df is None or df.empty:
        return False, "DataFrame is empty"
    
    required_cols = ['Distru Product', 'Category', 'Distru Batch Number', 'Available Quantity']
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    
    return True, "All required columns present"

def process_packages_to_audit(df):
    """
    Process packages DataFrame into audit sheet format
    
    Returns:
        DataFrame: Processed audit data with Brand column
    """
    # Make a copy
    audit_df = df.copy()
    
    # Extract brand
    audit_df['Brand'] = audit_df['Distru Product'].apply(extract_brand_from_product)
    
    # Convert quantity to numeric
    audit_df['System_Qty'] = audit_df['Available Quantity'].apply(lambda x: safe_numeric(x, 0))
    
    # Group by Category, Product, and Batch Number, sum quantities
    grouped = audit_df.groupby(
        ['Category', 'Brand', 'Distru Product', 'Distru Batch Number'], 
        dropna=False
    ).agg({
        'System_Qty': 'sum'
    }).reset_index()
    
    # Round quantities to integers
    grouped['System_Qty'] = grouped['System_Qty'].round().astype(int)
    
    # Sort by Category, then Brand, then Product
    grouped = grouped.sort_values(['Category', 'Brand', 'Distru Product', 'Distru Batch Number'])
    
    return grouped

# ============================================================================
# PDF GENERATION FUNCTIONS
# ============================================================================

def generate_audit_pdf(df, selected_categories, selected_brands, page_size='letter'):
    """
    Generate a professional audit PDF with checkboxes and signature lines
    
    Args:
        df: Filtered audit dataframe
        selected_categories: List of selected category names
        selected_brands: List of selected brand names
        page_size: 'letter' or 'a4'
        
    Returns:
        BytesIO: PDF file buffer
    """
    # Create buffer
    buffer = io.BytesIO()
    
    # Set page size
    pagesize = letter if page_size == 'letter' else A4
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        topMargin=0.5*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    # Title
    title = Paragraph("HAVEN DISTRIBUTION INVENTORY AUDIT WORKSHEET", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.1*inch))
    
    # Metadata section - condensed on fewer lines
    audit_date = datetime.now().strftime("%B %d, %Y")
    audit_time = datetime.now().strftime("%I:%M %p")
    
    # Filter info
    category_text = ", ".join(selected_categories) if selected_categories and 'All' not in selected_categories else "All Categories"
    brand_text = ", ".join(selected_brands) if selected_brands and 'All' not in selected_brands else "All Brands"
    
    # Count unique batches
    unique_batches = df['Distru Batch Number'].nunique()
    
    # Condensed metadata on 2 lines
    metadata = [
        f"<b>Date:</b> {audit_date} &nbsp;&nbsp;&nbsp; <b>Time:</b> {audit_time} &nbsp;&nbsp;&nbsp; <b>Unique Batches:</b> {unique_batches}",
        f"<b>Categories:</b> {category_text} &nbsp;&nbsp;&nbsp; <b>Brands:</b> {brand_text}"
    ]
    
    for line in metadata:
        elements.append(Paragraph(line, header_style))
    
    elements.append(Spacer(1, 0.15*inch))
    
    # Group by category
    categories = sorted(df['Category'].unique())
    
    for cat_idx, category in enumerate(categories):
        cat_data = df[df['Category'] == category].copy()
        
        # Category header
        cat_header = Paragraph(
            f"<b>Category: {category}</b> ({len(cat_data)} items)",
            styles['Heading2']
        )
        elements.append(cat_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Build table data - removed checkbox, brand, variance columns
        table_data = [
            ['Product', 'Batch #', 'System\nQty', 'Physical\nCount']
        ]
        
        # Style for wrapping text in cells
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10
        )
        
        for _, row in cat_data.iterrows():
            # Product name - truncate if too long
            product = str(row['Distru Product'])
            if len(product) > 60:
                product = product[:57] + "..."
            
            # Batch number as Paragraph to enable wrapping
            batch_text = str(row['Distru Batch Number'])
            batch_para = Paragraph(batch_text, cell_style)
            
            table_data.append([
                product,
                batch_para,  # Wrapped batch number
                str(row['System_Qty']),
                ''  # Empty for physical count
            ])
        
        # Create table with updated column widths
        # More space for Product, adequate space for Batch (with wrapping)
        col_widths = [4*inch, 1.5*inch, 0.7*inch, 0.9*inch]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table style
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Center qty columns
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for wrapping
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Page break after each category except the last
        if cat_idx < len(categories) - 1:
            elements.append(PageBreak())
    
    # Signature section on last page
    elements.append(Spacer(1, 0.3*inch))
    
    signature_table_data = [
        ['Audited By:', '_' * 40, 'Date:', '_' * 20],
        ['', '', '', ''],
        ['Verified By:', '_' * 40, 'Date:', '_' * 20]
    ]
    
    sig_table = Table(signature_table_data, colWidths=[1*inch, 3*inch, 0.7*inch, 1.8*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    
    # Reset buffer position
    buffer.seek(0)
    return buffer

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Title
    st.title(f"📋 DC Audit Report Generator v{VERSION}")
    st.markdown("Build custom physical audit sheets with PDF export")
    
    # Sidebar - Upload only
    st.sidebar.header("📊 Data Source")
    
    st.sidebar.subheader("📄 Upload Packages CSV")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Packages CSV:",
        type=['csv'],
        help="Upload the packages CSV export from Distru"
    )
    
    # Initialize session state for workflow
    if 'audit_df' not in st.session_state:
        st.session_state.audit_df = None
    if 'categories' not in st.session_state:
        st.session_state.categories = []
    if 'brands' not in st.session_state:
        st.session_state.brands = []
    
    # Main content
    if not uploaded_file:
        st.info("👈 **Step 1:** Upload a packages CSV file to begin building your audit report")
        
        # Show example format
        with st.expander("📖 Expected CSV Format"):
            st.markdown("""
            Your CSV should contain these columns:
            - **Distru Product**: Full product name (e.g., "Brand - Product Description")
            - **Category**: Product category (e.g., "Vape", "Flower (Indica)", "Gummies")
            - **Distru Batch Number**: Batch identifier
            - **Available Quantity**: Quantity available in package
            
            The brand will be automatically extracted from the product name.
            """)
        return
    
    # Load and process data
    if st.session_state.audit_df is None:
        with st.spinner("🔄 Processing packages data..."):
            packages_df = load_packages_csv(uploaded_file)
            
            if packages_df is None:
                st.error("❌ Failed to load CSV file")
                return
            
            # Validate
            valid, message = validate_required_columns(packages_df)
            if not valid:
                st.error(f"❌ {message}")
                return
            
            # Process
            audit_df = process_packages_to_audit(packages_df)
            st.session_state.audit_df = audit_df
            st.session_state.categories = sorted(audit_df['Category'].unique().tolist())
            st.session_state.brands = sorted(audit_df['Brand'].unique().tolist())
    
    audit_df = st.session_state.audit_df
    
    # ========================================================================
    # REPORT BUILDER SECTION
    # ========================================================================
    
    st.markdown("---")
    st.header("🔨 Build Your Audit Report")
    st.markdown("Configure your report by selecting categories and brands to include in the physical audit.")
    
    # Create two columns for the builder
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📂 Step 2: Select Categories")
        
        # Quick select buttons
        select_col1, select_col2 = st.columns(2)
        with select_col1:
            if st.button("✅ Select All Categories", use_container_width=True):
                st.session_state.selected_categories = ['All']
        with select_col2:
            if st.button("❌ Clear Categories", use_container_width=True):
                st.session_state.selected_categories = []
        
        # Category selector
        category_options = ['All'] + st.session_state.categories
        
        if 'selected_categories' not in st.session_state:
            st.session_state.selected_categories = ['All']
        
        selected_categories = st.multiselect(
            "Categories to include:",
            options=category_options,
            default=st.session_state.selected_categories,
            help="Select specific categories or 'All' for complete inventory audit",
            key="category_selector"
        )
        
        # Update session state
        st.session_state.selected_categories = selected_categories
        
        # Show count
        if selected_categories and 'All' not in selected_categories:
            cat_filtered = audit_df[audit_df['Category'].isin(selected_categories)]
            st.info(f"📦 {len(cat_filtered):,} items in selected categories")
    
    with col2:
        st.subheader("🏷️ Step 3: Select Brands")
        
        # Quick select buttons
        select_col3, select_col4 = st.columns(2)
        with select_col3:
            if st.button("✅ Select All Brands", use_container_width=True):
                st.session_state.selected_brands = ['All']
        with select_col4:
            if st.button("❌ Clear Brands", use_container_width=True):
                st.session_state.selected_brands = []
        
        # Brand selector
        brand_options = ['All'] + st.session_state.brands
        
        if 'selected_brands' not in st.session_state:
            st.session_state.selected_brands = ['All']
        
        selected_brands = st.multiselect(
            "Brands to include:",
            options=brand_options,
            default=st.session_state.selected_brands,
            help="Select specific brands or 'All' for all brands",
            key="brand_selector"
        )
        
        # Update session state
        st.session_state.selected_brands = selected_brands
        
        # Show count
        if selected_brands and 'All' not in selected_brands:
            brand_filtered = audit_df[audit_df['Brand'].isin(selected_brands)]
            st.info(f"🏷️ {len(brand_filtered):,} items from selected brands")
    
    # Apply filters
    filtered_df = audit_df.copy()
    
    if selected_categories and 'All' not in selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]
    
    if selected_brands and 'All' not in selected_brands:
        filtered_df = filtered_df[filtered_df['Brand'].isin(selected_brands)]
    
    # ========================================================================
    # PREVIEW & GENERATE SECTION
    # ========================================================================
    
    st.markdown("---")
    st.header("📄 Step 4: Preview & Generate Report")
    
    if filtered_df.empty:
        st.warning("⚠️ No items match your selection. Please adjust your filters.")
        return
    
    # Summary metrics
    st.subheader("📊 Report Summary")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("Total Items", f"{len(filtered_df):,}")
    with metric_col2:
        st.metric("Unique Batches", f"{filtered_df['Distru Batch Number'].nunique():,}")
    with metric_col3:
        st.metric("Categories", f"{filtered_df['Category'].nunique():,}")
    with metric_col4:
        total_qty = filtered_df['System_Qty'].sum()
        st.metric("System Qty", f"{int(total_qty):,}")
    
    # Preview by category
    st.subheader("🔍 Report Preview")
    
    categories_in_report = sorted(filtered_df['Category'].unique())
    
    for category in categories_in_report:
        cat_data = filtered_df[filtered_df['Category'] == category]
        cat_qty = cat_data['System_Qty'].sum()
        
        with st.expander(f"📦 {category} ({len(cat_data):,} items, {int(cat_qty):,} units)", expanded=False):
            # Show top 10 items - match PDF columns
            display_cols = ['Distru Product', 'Distru Batch Number', 'System_Qty']
            display_df = cat_data[display_cols].head(10).copy()
            display_df.columns = ['Product', 'Batch #', 'System Qty']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            if len(cat_data) > 10:
                st.info(f"Showing first 10 of {len(cat_data):,} items. Full list will be in PDF.")
    
    # ========================================================================
    # PDF GENERATION
    # ========================================================================
    
    st.markdown("---")
    st.subheader("📥 Step 5: Download Audit Report")
    
    col_pdf1, col_pdf2 = st.columns([2, 1])
    
    with col_pdf1:
        st.markdown("""
        **Your audit report includes:**
        - ✅ Header with date, time, unique batch count, and filter details
        - ✅ Grouped by category for easy organization
        - ✅ Product names and batch numbers (with text wrapping)
        - ✅ System quantity column for expected counts
        - ✅ Physical count column for manual entry during audit
        - ✅ Signature lines for auditor and verifier
        """)
    
    with col_pdf2:
        page_size = st.radio(
            "Paper Size:",
            options=['letter', 'a4'],
            index=0,
            format_func=lambda x: 'Letter (8.5" x 11")' if x == 'letter' else 'A4'
        )
    
    # Generate PDF button
    if st.button("🎯 Generate Audit PDF", type="primary", use_container_width=True):
        with st.spinner("📄 Generating your audit report..."):
            try:
                # Generate PDF
                pdf_buffer = generate_audit_pdf(
                    filtered_df,
                    selected_categories,
                    selected_brands,
                    page_size
                )
                
                # Create filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                category_part = "_".join(selected_categories[:2]) if selected_categories and 'All' not in selected_categories else "All"
                filename = f"DC_Audit_{category_part}_{timestamp}.pdf"
                
                # Download button
                st.success("✅ Report generated successfully!")
                st.download_button(
                    label="📥 Download Audit Report PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
                st.exception(e)
    
    # ========================================================================
    # DEBUG TAB (Optional)
    # ========================================================================
    
    with st.expander("🔍 Debug Information"):
        st.write("**Data Statistics:**")
        st.write(f"- Total packages loaded: {len(audit_df):,}")
        st.write(f"- After filtering: {len(filtered_df):,}")
        st.write(f"- Available categories: {len(st.session_state.categories)}")
        st.write(f"- Available brands: {len(st.session_state.brands)}")
        
        st.write("\n**Sample Data:**")
        st.dataframe(filtered_df.head(10), use_container_width=True)
    
    # Changelog in sidebar
    with st.sidebar.expander("📋 Version History"):
        st.markdown("""
        **v2.0** (Current)
        - Redesigned with "Report Builder" workflow
        - Added PDF generation for physical audits
        - Moved filters to main content area
        - Added audit-friendly formatting
        - Signature lines and metadata
        
        **v1.0** (2025-11-07)
        - Initial CSV processing release
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Version {VERSION}**")

if __name__ == "__main__":
    main()