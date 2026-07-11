import os
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"

DOCS = {
    "ongc_overview/asset_management.md": """# ONGC Asset Management Guidelines

This document outlines the standard operating procedures and guidelines for the lifecycle management of capital and operating assets at ONGC.

## Asset Lifecycle Management
ONGC manages a vast portfolio of physical assets including offshore platforms, drilling rigs, onshore processing plants, pipelines, and corporate offices. The lifecycle comprises:
1. **Acquisition & Commissioning**: Assets must be cataloged in the ERP system upon successful site commissioning.
2. **Operations & Maintenance**: Standard maintenance schedules (preventive, predictive, and corrective) must be logged in the Asset Register.
3. **Decommissioning & Disposal**: Assets that have reached the end of their design life or are economically unviable must go through a formal technical evaluation and disposal bidding process.

## Capital Asset Register (CAR)
- Every asset is assigned a unique Asset Identification Number (AIN).
- Depreciation is calculated using straight-line methods in accordance with corporate accounting policies.
- Physical verification of assets is conducted annually by designated inspection teams.
""",

    "exploration_drilling/exploration.md": """# ONGC Exploration Workflows

ONGC is a pioneer in oil and gas exploration in India. This document details the workflows followed by the Exploration division.

## Exploration Stages
1. **Basin Analysis & G&G Surveys**: Initial assessment using gravity, magnetic, and 2D/3D seismic surveys to map structural traps.
2. **Prospect Identification**: Processing and interpreting seismic data using advanced workstations to identify potential hydrocarbon reserves.
3. **Exploratory Drilling**: Drilling wildcat wells to test the geological structures and determine the presence of hydrocarbons.

## Seismic Data Acquisition & Processing
- High-resolution 3D seismic acquisition is preferred for complex fault structures.
- Processing involves noise attenuation, migration (e.g., Pre-Stack Depth Migration), and depth conversion.
- Quality control is managed by the Geophysics Division at corporate headquarters.
""",

    "exploration_drilling/drilling.md": """# ONGC Drilling Workflows and Procedures

Drilling operations are critical to ONGC's upstream activities. This document outlines drilling procedures, rig classification, and casing design.

## Drilling Operations
- **Well Planning**: Involves choosing the target depth, trajectory (vertical, directional, horizontal), and predicting pore pressures.
- **Rig Selection**: Jack-up rigs, drillships, or semi-submersibles are selected based on water depth and environmental conditions.
- **Drilling Fluid (Mud) Management**: Water-based mud (WBM) or synthetic-based mud (SBM) is used to control well pressure, cool the bit, and transport cuttings to the surface.

## Well Casing & Cementing
- Conductor, surface, intermediate, and production casing strings must be designed to withstand collapse, burst, and tension forces.
- Cementing operations must ensure complete zonal isolation. A cement bond log (CBL) must be run to verify cementing quality before resuming drilling.
""",

    "exploration_drilling/reservoir_engineering.md": """# ONGC Reservoir Engineering and Management

Reservoir engineering optimizes hydrocarbon recovery from ONGC fields. This document explains logging, pressure analysis, and recovery techniques.

## Reservoir Characterization
- **Well Logging**: Electrical, nuclear, and acoustic logs are analyzed to estimate porosity, water saturation, and permeability.
- **PVT Analysis**: Pressure-Volume-Temperature analysis is conducted on fluid samples to define fluid properties and phase behavior.

## Enhanced Oil Recovery (EOR)
- **Primary Recovery**: Natural reservoir pressure drives fluid to the wellbore.
- **Secondary Recovery**: Waterflooding or gas injection is implemented to maintain reservoir pressure.
- **Tertiary/EOR**: Thermal, chemical, or gas injection techniques (e.g., CO2 flooding) are used to extract remaining oil.
- All EOR plans require approval from the Director (Exploration & Development).
""",

    "production_operations/production.md": """# ONGC Production Operations

ONGC's production operations cover the processing, separation, and transport of crude oil and natural gas.

## Production Facilities
- **Group Gathering Stations (GGS)**: Collect fluids from onshore wells, separate gas and water, and pump crude to central processing facilities.
- **Offshore Process Platforms**: Perform high-capacity separation, dehydration, gas compression, and water injection.

## Fluid Separation Process
1. **Three-Phase Separation**: Separates crude oil, gas, and free water.
2. **Oil Dehydration**: Thermochemical treatment is used to reduce water content to less than 0.5% (Basic Sediment and Water - BS&W).
3. **Gas Dehydration**: Glycol absorption units remove moisture to prevent hydrate formation in pipelines.
""",

    "production_operations/offshore_operations.md": """# ONGC Offshore Operations Guidelines

Offshore production is responsible for a significant share of ONGC's total hydrocarbon output.

## Platform Operations
- **Manned Platforms**: e.g., Mumbai High North (MHN), Mumbai High South (MHS), which feature processing equipment, living quarters, and helidecks.
- **Unmanned Platform (Wellheads)**: Distribute production to process platforms via subsea pipelines. Regular maintenance is performed by offshore supply vessels (OSVs).

## Subsea Engineering
- Subsea wells use subsea trees, manifolds, and control umbilicals tied back to floating production units (FPSOs) or fixed platforms.
- Integrity of subsea structures must be inspected annually using ROVs (Remotely Operated Vehicles).
""",

    "production_operations/project_management.md": """# ONGC Project Management Framework

All major capital expenditures and facility construction projects follow a structured project management methodology.

## Front-End Loading (FEL) Stages
- **FEL-1 (Feasibility)**: Defines business case, preliminary scope, and cost estimates.
- **FEL-2 (Conceptual Design)**: Selects technical options, layout, and updates cost estimates to +/- 20%.
- **FEL-3 (FEED)**: Front-End Engineering Design, develops tender packages for Engineering, Procurement, and Construction (EPC) contracts.

## Project Execution & Controls
- Progress is tracked using Earned Value Management (EVM).
- Variations in scope must be approved by the Project Monitoring Group (PMG) and the competent authority according to the Book of Delegated Powers.
""",

    "production_operations/quality_assurance.md": """# ONGC Quality Assurance and Quality Control (QA/QC)

This document details quality protocols for engineering materials, equipment, and services across ONGC.

## QC Standards & Inspections
- All equipment must comply with API, ASME, ASTM, and Indian Standards (BIS).
- Third-Party Inspection (TPI) agencies (e.g., DNV, Lloyds, IRS) must verify and certify safety-critical equipment prior to delivery.
- Mill test certificates (MTC) and non-destructive testing (NDT) logs must be archived for all structural steels and pressure vessels.
""",

    "governance_compliance/corporate_governance.md": """# ONGC Corporate Governance Framework

ONGC is committed to transparency, integrity, and accountability. This document outlines the corporate governance structure.

## Board of Directors
- The Board consists of Executive Directors (including the Chairman and Managing Director - CMD), Government Nominee Directors, and Independent Directors.
- Board Committees include the Audit Committee, Nomination and Remuneration Committee, CSR Committee, and Stakeholder Relationship Committee.

## Code of Conduct
- Every employee must comply with the ONGC Code of Conduct, which prohibits conflicts of interest, bribery, insider trading, and harassment.
- Annual disclosures of assets, liabilities, and external interests are mandatory for all executives.
""",

    "governance_compliance/compliance.md": """# ONGC Regulatory Compliance Guidelines

ONGC operates within a strict legal framework. This document outlines compliance requirements for corporate, statutory, and environmental regulations.

## Key Regulatory Bodies
- **Directorate General of Hydrocarbons (DGH)**: Oversees compliance with Production Sharing Contracts (PSCs) and Revenue Sharing Contracts (RSCs).
- **Ministry of Petroleum and Natural Gas (MoPNG)**: Formulates policy and issues licenses.
- **Securities and Exchange Board of India (SEBI)**: Regulates listed entities, demanding quarterly financial disclosures and reporting of price-sensitive information.

## Compliance Audits
- Compliance status is reviewed quarterly by the Legal and Secretarial department.
- Any non-compliance must be reported to the Audit Committee immediately.
""",

    "sustainability_csr/sustainability.md": """# ONGC Sustainability and ESG Commitments

ONGC aims to balance energy security with environmental stewardship. This document details our sustainability roadmap.

## Net-Zero Targets
- ONGC is aiming to achieve Net-Zero Scope 1 and Scope 2 carbon emissions by 2038.
- Strategies include gas flaring reduction, electrification of offshore facilities, carbon capture utilization and storage (CCUS), and investment in solar/wind energy.

## ESG Disclosures
- Sustainability reporting follows the Global Reporting Initiative (GRI) standards.
- Progress on greenhouse gas emission reductions is verified by external green auditors annually.
""",

    "sustainability_csr/environment.md": """# ONGC Environmental Management Policy

ONGC is dedicated to minimizing its ecological footprint across all operations.

## Environmental Impact Assessment (EIA)
- An EIA must be conducted before initiating any new exploration, drilling, or development project.
- Public hearings and approvals from the Ministry of Environment, Forest and Climate Change (MoEFCC) are mandatory.

## Waste Management and Oil Spill Response
- **Produced Water**: Treated to meet regulatory standards (oil content < 10 ppm) before disposal or reinjection.
- **Drill Cuttings**: Treated with oil removal systems (thermal desorption units) before landfilling.
- **Oil Spill Response (OSR)**: ONGC maintains Tier-1 OSR equipment at all offshore hubs and has contracts for Tier-2 and Tier-3 offshore spill responses.
""",

    "hse/workplace_safety.md": """# ONGC Workplace Safety Standard Operating Procedures

Safety is our top priority. This document provides core workplace safety rules applicable at all sites.

## Daily Briefs & Tool Box Talks (TBT)
- A Toolbox Talk must be conducted at the start of every shift by the supervisor.
- The TBT must address the specific jobs for the day, hazards associated with them, and required control measures.

## General Safety Rules
- Horseplay, unauthorized entry, and working without correct authorization are strictly prohibited.
- "Stop Work Authority" empowers every employee and contractor to halt any job if they observe an unsafe condition or act.
- Report all near-misses immediately to the Safety Officer using the online portal.
""",

    "hse/permit_to_work.md": """# ONGC Permit to Work (PTW) System

The Permit to Work (PTW) system is a formal written safety procedure used to control safety-critical work at ONGC.

## What is PTW?
PTW is a document that specifies the task, hazards, precautions, PPE, and authorizations required before carrying out non-routine or hazardous work.

## PTW Classifications
1. **Hot Work Permit (Red)**: Required for activities involving open flames, sparks, welding, cutting, or grinding in hazardous areas.
2. **Cold Work Permit (Blue)**: Required for general maintenance, excavation, working at heights, or civil works that do not involve ignition sources.
3. **Confined Space Entry Permit**: Mandatory for entering tanks, vessels, sumps, or sewers. Requires continuous gas testing (oxygen, toxic gases, flammables).

## Approval Flow
- **Requestor (Performer)**: Initiates the permit detailing the scope of work.
- **Issuer (Area In-Charge)**: Conducts risk assessment, defines isolation points, and signs the authorization.
- **Safety Officer**: Over-checks critical permits (e.g., Confined Space, Hot Work in Process Areas) and performs gas checks.
- All permits must be closed or suspended at the end of the shift.
""",

    "hse/incident_reporting.md": """# ONGC Incident Reporting and Investigation Procedures

Accurate incident reporting ensures lessons are learned and prevents recurrence.

## Incident Classification
- **Near Miss**: Unplanned event that did not result in injury or damage, but had the potential to do so.
- **First Aid Case**: Minor injuries treated on-site.
- **Lost Time Injury (LTI)**: Injury resulting in absence from work for 48 hours or more.
- **Fatal Incident**: Loss of life.

## Reporting Timelines
- All incidents and near-misses must be logged on the HSE portal within **24 hours**.
- Serious incidents or fatalities must be reported to corporate management and regulators within **4 hours** of occurrence.

## Investigation Workflow
1. **Scene Securing**: Prevent alteration of physical evidence.
2. **Root Cause Analysis (RCA)**: Conducted using TapRooT, 5-Whys, or Fishbone analysis by an independent committee.
3. **Action Items**: Create corrective and preventive actions (CAPA), tracking them to completion in the HSE database.
""",

    "hse/emergency_response.md": """# ONGC Emergency Response and Preparedness Plan

This manual defines the procedures for managing crises and emergencies at ONGC installations.

## Emergency Response Organization
- **Incident Commander (IC)**: The senior manager on-site who takes command of emergency operations.
- **Emergency Control Center (ECC)**: The designated command room equipped with communication lines, plant status displays, and muster records.
- **Emergency Response Team (ERT)**: Trained personnel responsible for firefighting, rescue, and medical first-aid.

## Muster and Evacuation
- Upon hearing the emergency siren (continuous warbling tone), all personnel must immediately proceed to their assigned **Muster Points**.
- Floor marshals must verify headcounts against the daily gate log and report to the ECC.
- Helicopter or lifeboat evacuation is coordinated by the ECC and offshore coordinators.
""",

    "hse/fire_safety.md": """# ONGC Fire Safety and Protection Systems

This document describes fire prevention, detection, and suppression systems.

## Fire Detection
- Heat, smoke, and flame detectors are installed throughout process areas, control rooms, and offices.
- Gas detectors (Hydrocarbon, H2S) trigger alarms at the Central Control Room when concentration exceeds 10% LEL.

## Fire Suppression
- **Deluge Systems**: Automactically spray water/foam over process vessels and hydrocarbon storage tanks.
- **Portable Fire Extinguishers**: CO2 (electrical fires), Dry Chemical Powder (DCP) for class A/B/C fires, and Foam extinguishers must be inspected monthly.
- **Fire Hydrant Ring**: Maintained at a pressure of 7 kg/cm² across all processing facilities.
""",

    "hse/ppe_guidelines.md": """# ONGC Personal Protective Equipment (PPE) Guidelines

Personal Protective Equipment (PPE) is the final line of defense against workplace hazards.

## Mandatory PPE at Operational Sites
At all operational wells, platforms, GGSs, and plants, the following PPE is mandatory:
- **Safety Helmet (Hard Hat)**: Protects against falling objects.
- **Safety Boots**: Steel-toed boots with slip-resistant and anti-static soles.
- **Flame-Resistant Clothing (FRC)**: Double-stitched, 100% cotton treated fabric, or Nomex coveralls to protect against flash fires.
- **Safety Glasses**: Polycarbonate impact-resistant lenses.

## Task-Specific PPE
- **Welding Face Shield & Leather Apron**: Required for hot work.
- **Full Body Safety Harness**: Mandatory for work at heights above 1.8 meters. Must be anchored to an approved lifeline.
- **Chemical Goggles & Rubber Apron**: Required when handling acids, caustic sodas, or drilling chemical additives.
- **SCBA (Self-Contained Breathing Apparatus)**: Required for confined space entry or in areas with toxic gas leaks (e.g., H2S).
""",

    "hse/hazard_identification.md": """# ONGC Hazard Identification Guidelines

Identifying hazards before they lead to accidents is central to ONGC's safety culture.

## Hazard Types
- **Physical**: Noise, vibration, temperature extremes, high pressure, radiation.
- **Chemical**: Hydrocarbons, hydrogen sulfide (H2S), acids, solvents.
- **Ergonomic**: Poor posture, heavy lifting, repetitive motion.
- **Biological**: Pathogens, contaminated water, insect bites.

## Hazard Reporting
- Hazard reports are submitted using the Hazard Observation (HAZOB) card system.
- Cards are color-coded: Orange for unsafe acts, Yellow for unsafe conditions.
- Supervisors must review all HAZOB cards daily and initiate work orders to mitigate hazards.
""",

    "hse/risk_assessment.md": """# ONGC Risk Assessment Methodology

Risk assessment evaluates the severity and likelihood of hazards to establish control measures.

## Risk Assessment Tools
1. **Job Safety Analysis (JSA)**: Breaks down a task step-by-step to identify hazards at each stage and document controls. Mandatory for non-routine works.
2. **HAZOP (Hazard and Operability Study)**: Systematic, interdisciplinary review of process designs using guidewords (e.g., No Flow, High Temp) to identify design deficiencies.
3. **Risk Matrix**: A 5x5 matrix evaluating Likelihood (Rare to Frequent) vs. Consequence (Negligible to Catastrophic).
   - High-risk activities (Red zone) must be approved by the Asset Manager and require a formal JSA and PTW.
""",

    "procurement/procurement_process.md": """# ONGC Procurement Process and Tendering Guidelines

ONGC's procurement process complies with public procurement norms to ensure transparency and efficiency.

## Procurement Workflows
1. **Requisition (Indenting)**: The user department raises an indent in the ERP system detailing the specifications and estimated cost.
2. **Tender Approval**: Tender committee approves the bidding mode (Open Tender, Limited Tender, or Single Tender for proprietary items).
3. **Bidding Stage**: Tenders are published on the e-procurement portal. Bidders submit technical and financial bids separately (Two-bid system).
4. **Evaluation & Award**: Technical bids are opened and evaluated first. Financial bids of only technically qualified bidders are opened. The contract is awarded to the lowest responsive bidder (L1).

## Purchase Order (PO) Execution
- A formal PO or contract is signed.
- Performance Bank Guarantees (PBG) are secured from vendors to cover warranty periods.
""",

    "procurement/vendor_management.md": """# ONGC Vendor Management Policy

This document outlines policies for registering, evaluating, and managing vendors.

## Vendor Registration
- New vendors must register on the e-procurement portal, submitting financial statements, technical credentials, and compliance certificates.
- Physical site audits may be conducted by the Quality division.

## Performance Rating & Blacklisting
- Vendor performance is evaluated on delivery schedule adherence, material quality, and safety compliance.
- Substandard performance leads to warnings, suspension, or formal blacklisting (banning from bidding in future ONGC tenders) for a period of 2 to 5 years.
""",

    "finance_accounts/finance_rules.md": """# ONGC Corporate Finance Rules and Regulations

This document summarizes finance workflows, verification protocols, and accounting standards.

## Delegation of Financial Powers (DoFP)
- Financial approvals are governed by the Book of Delegated Powers (BDP).
- Each executive level has specific monetary limits for capital (CAPEX) and revenue (OPEX) sanctions.
- Exceeding these limits requires approval from the next authority level or the Board.

## Invoice Processing & Payment
- Invoices must be submitted with goods receipt notes (GRN), inspection reports, and sign-offs from the user department.
- Automated ERP workflows route invoices for tax verification (GST compliance) and bank clearance.
""",

    "finance_accounts/budget_planning.md": """# ONGC Budget Planning Guidelines

ONGC plans budgets annually to balance capital investment with shareholder returns.

## Budget Classification
- **CAPEX (Capital Expenditure)**: Covers purchasing rigs, building platforms, seismic surveys, development drilling, and IT infrastructure.
- **OPEX (Operational Expenditure)**: Covers maintenance, consumables, fuel, salaries, rental equipment, and routine services.

## Variance Analysis
- Monthly expenditures are compared against approved budgets in the ERP system.
- Departments with variances exceeding +/- 10% must provide justifications to the Finance Committee.
""",

    "finance_accounts/internal_audit.md": """# ONGC Internal Audit Procedures

Internal Audit ensures operational efficiency, financial compliance, and risk management.

## Audit Planning
- The Internal Audit team operates independently and reports to the Audit Committee.
- Annual audit plans target high-risk operations, procurement contracts exceeding 5 Crores, and inventory control at storage hubs.

## Findings & Remediation
- Audit observations are shared with the department heads who must provide corrective action plans (CAPA) with clear timelines.
- Remediation progress is tracked in the GRC (Governance, Risk, and Compliance) dashboard.
""",

    "human_resources/leave_policy.md": """# ONGC Leave Rules and Policies

This document covers leave entitlements, accruals, and approvals for all employees.

## Entitlements (Annual)
- **Earned Leave (EL)**: 30 days per year, credited in two installments of 15 days on January 1st and July 1st. Accumulation is allowed up to 300 days.
- **Casual Leave (CL)**: 12 days per calendar year. Unused CL lapses at the end of the year.
- **Commuted (Medical) Leave**: 20 days on half pay (convertible to 10 days on full pay with a medical certificate).
- **Maternity Leave**: 180 days for female employees.
- **Paternity Leave**: 15 days for male employees.

## Approval Workflows
- All leave requests must be submitted through the ESS (Employee Self Service) portal.
- Casual leave requires approval from the immediate supervisor. Earned leave of more than 5 days must be requested at least 15 days in advance.
""",

    "human_resources/recruitment.md": """# ONGC Recruitment and Induction Guidelines

ONGC hires talented professionals through structured recruitment frameworks.

## Cadre Classification
- **A-Level (Executives)**: Recruited through national examinations (e.g., GATE scores for engineers) followed by group discussions and interviews.
- **B-Level & C-Level (Non-Executives)**: Recruited through localized open notifications and competitive tests.

## Induction and Probation
- Executive trainees undergo 1 year of probation.
- Probation completion requires successful completion of the induction program, technical training, and an appraisal review.
""",

    "human_resources/employee_benefits.md": """# ONGC Employee Welfare and Benefits Manual

ONGC offers comprehensive benefits to support its employees and their families.

## Medical Benefits
- **PRMBS (Post-Retirement Medical Benefit Scheme)**: Provides lifelong cashless medical coverage at paneled hospitals for retired employees and their spouses.
- Working employees receive full coverage for medical treatment, hospitalizations, and specialized therapies.

## Housing & Allowances
- Company-leased accommodation or House Rent Allowance (HRA) is provided.
- Allowances include Conveyance Allowance, Drilling Allowance (for offshore/field personnel), and Professional Development Allowance (for books, journals, and professional memberships).
""",

    "human_resources/training.md": """# ONGC Corporate Training and Development Policy

ONGC is committed to continuous learning and capacity building.

## Training Institutes
ONGC operates specialized training academies:
- **IMD (Institute of Management Development)**, Dehradun: Focuses on leadership, strategy, and management.
- **IPSHEM (Institute of Petroleum Safety, Health and Environment Management)**, Goa: Focuses on safety drills, emergency responses, and survival training.
- **IDT (Institute of Drilling Technology)**, Dehradun: Specialized courses in drilling dynamics, blowout prevention (IWCF certification), and well control.

## Training Mandates
- Every field employee must undergo refresher safety training at IPSHEM every 3 years.
- Executive development training is tied to promotions.
""",

    "it_cybersecurity/it_policies.md": """# ONGC IT Infrastructure and Asset Policies

This policy outlines acceptable use guidelines for computer assets, networks, and software.

## Computer Usage Rules
- All desktop computers and laptops provided by the company are corporate assets and subject to audit.
- Unlicensed software installation is strictly prohibited. Only software approved by the IT department may be installed.
- USB drives are disabled on corporate terminals unless explicitly authorized by the Security Officer for operational purposes.

## Internet & Network Access
- Corporate email is restricted to business communications.
- VPN access is restricted to authorized employees and requires approval from the Chief Information Officer (CIO).
""",

    "it_cybersecurity/cyber_security.md": """# ONGC Cybersecurity Regulations

ONGC protects critical infrastructure from cyber threats using layered security controls.

## Authentication and Passwords
- Passwords must be at least 12 characters, including uppercase, lowercase, numbers, and special symbols.
- Password change is enforced every 60 days.
- Multi-Factor Authentication (MFA) is mandatory for remote logins, VPNs, and corporate email access.

## Cyber Incident Response
- Any suspected phishing email, malware warning, or unauthorized system access must be reported to the CERT (Computer Emergency Response Team) immediately at cert@ongc.co.in.
- Compromised accounts will be locked automatically.
""",

    "it_cybersecurity/digital_transformation.md": """# ONGC Digital Transformation and Innovation Roadmap

ONGC leverages digital technologies to enhance production efficiency and reduce costs.

## Key Initiatives
- **EPINET**: Comprehensive enterprise database for exploration and production data.
- **Digital Oilfield (DOF)**: Real-time monitoring of wells, pipelines, and GGSs using IoT sensors, enabling predictive maintenance.
- **SCADA Integrations**: Centralized supervisory control and data acquisition for offshore platforms and gas pipelines.
- **AI/ML Analytics**: Deployed to analyze seismic logs and predict reservoir behavior.
"""
}

def generate_docs():
    for filepath, content in DOCS.items():
        full_path = KB_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure file content is stripped and clean
        cleaned_content = content.strip() + "\n"
        full_path.write_text(cleaned_content, encoding="utf-8")
        print(f"Generated: {full_path}")

if __name__ == "__main__":
    generate_docs()
