# Manufacturing Analytics & Execution Platform

**Master Project Rules, Product Vision, Raw Materials & Development Specification**

- **Document Type:** Master Project Rules / Product Constitution
- **Status:** Foundational
- **Version:** 0.1
- **Purpose:** Permanent source of truth for human developers and AI development assistants
- **Initial Target Plant:** Existing roof-tile / ceramic manufacturing plant that supplied the historical production data
- **Target Product:** Configurable Manufacturing Analytics & Execution Platform

> Converted to Markdown from `Manufacturing Analytics & Execution Platform Master Project Rules.docx` (v0.1). Content is verbatim; only formatting (headings, lists, code blocks, tables) has been applied.

---

## 1. IMPORTANT INSTRUCTION TO ALL AI DEVELOPMENT ASSISTANTS

This document is the permanent project memory.

Any AI assistant working on this project MUST treat this document and its approved companion documents as the project's source of truth.

Before generating, modifying, deleting, or restructuring code, the AI MUST understand:

- The product is a configurable manufacturing platform, not software hardcoded for one factory.
- The initial implementation is based on a real roof-tile manufacturing plant and its existing historical data.
- The initial plant's data is extremely valuable and must not be discarded.
- At least 15 years of historical manufacturing data may exist and must be importable and analyzable.
- Historical data must remain available for trend analysis, benchmarking, statistical analysis, charts, forecasting, machine learning, and continuous improvement.
- Existing Excel workbooks are raw operational data sources, not the final database architecture.
- The new system must replace fragmented Excel-based operational recording with a centralized application and database.
- The platform must support different types of roof-tile, brick, ceramic, masonry, and potentially other manufacturing plants.
- Manufacturing workflows must be configurable rather than hardcoded.
- Analytics is a first-class capability of the platform.
- The system must preserve traceability from high-level KPIs back to the underlying production records.
- AI must never silently invent business rules, database relationships, production formulas, or manufacturing assumptions.
- When requirements are unclear, the AI must identify the uncertainty rather than inventing a fact.
- Existing data must be treated as evidence of the current plant's real-world process, not automatically treated as the ideal future design.
- The architecture must distinguish between:
  - generic platform concepts,
  - configurable manufacturing concepts,
  - and factory-specific implementation details.
- The system must be designed so that the first factory is the reference implementation, not the permanent architectural limitation.

---

## 2. PRODUCT VISION

The product is a:

**Manufacturing Analytics & Execution Platform**

The platform is intended to digitize manufacturing operations while transforming historical and real-time production data into useful operational intelligence.

It is not merely:

- an Excel replacement,
- a CRUD application,
- a production log,
- or a reporting dashboard.

It is intended to become a manufacturing intelligence platform capable of answering:

- **What happened?** — Historical and operational reporting.
- **What is happening?** — Current production monitoring.
- **Why did it happen?** — Statistical analysis, correlations, comparisons, and root-cause analysis.
- **What will happen?** — Forecasting and predictive analytics.
- **What should we do?** — Recommendations, optimization, alerts, and eventually AI-assisted decision support.

---

## 3. INITIAL FACTORY

The first implementation is based on an existing roof-tile / ceramic manufacturing plant.

The plant currently uses multiple Excel workbooks and production tables.

The initial project has already collected real operational data from this plant.

This existing plant is the source of the initial domain knowledge and the first implementation requirements.

However:

- The application MUST NOT be architecturally hardcoded around this factory.
- The first plant is the first tenant / reference implementation from which the platform's generic manufacturing model will be validated.

---

## 4. CORE PRODUCT PRINCIPLE

The platform must separate three levels of information.

### Level 1 — Platform

Generic concepts that apply to almost every manufacturing organization.

Examples:

Company, Factory, Plant, Production Line, Department, User, Employee, Role, Shift, Product, Equipment, Work Order, Batch, Operation, Inspection, Quality Result, Waste, KPI, Event, Alert

### Level 2 — Configurable Manufacturing

Concepts whose structure varies by factory.

Examples:

Production stages, Process workflows, Equipment types, Quality characteristics, Product attributes, Recipes, Production parameters, KPI definitions, Inspection forms, Production rules, Shift patterns, Units of measure

### Level 3 — Industry / Factory Specific

Examples from the initial plant:

Roof tile, Clay body, Mold, Dryer chamber, Finger car, Wagon, Kiln, Glazing, Grade 1, Dryer waste, Specific mold codes, Specific product codes, Existing operator codes, Existing supervisor codes

These must be implemented through configuration or an industry-specific module wherever possible.

---

## 5. INITIAL MANUFACTURING PROCESS UNDERSTANDING

The initial factory's production process currently understood from the supplied data is approximately:

```
Raw / Formed Ceramic Product
        ↓
Tray / Finger Handling
        ↓
Dryer Loading
        ↓
Drying
        ↓
Dryer Unloading
        ↓
Transfer / Wagon Arrangement
        ↓
Kiln
        ↓
Sorting / Grading
        ↓
Quality Measurement
        ↓
Waste / Scrap Classification
        ↓
Finished Production
```

The actual factory process must be validated against the plant's operational staff before the final workflow engine is frozen.

The system MUST NOT assume that this workflow is universal.

A different plant may use:

```
Mixing → Extrusion → Cutting → Drying → Kiln → Sorting → Packaging
```

or:

```
Pressing → Glazing → Drying → Firing → Inspection → Packaging
```

The platform must support these through configuration.

---

## 6. CURRENT DATA SOURCES

The current project has supplied several related datasets.

These datasets are considered raw materials for domain discovery, migration, validation, analytics, and historical import.

They must NOT simply be copied blindly into the final database.

Instead:

```
Existing Excel Data
        ↓
Data Profiling
        ↓
Data Mapping
        ↓
Data Cleaning
        ↓
Data Validation
        ↓
Historical Import Layer
        ↓
Normalized Manufacturing Database
```

---

## 7. DATASET A — DRYER / CHAMBER LOAD-UNLOAD DATA

The supplied table contains:

```
ChamberNo
LoadDateJalali
LoadTime
LoadOperatorCode_FK
ProductCode_FK
UnloadDateJalali
UnloadTime
LoadOperatorCode_FK.1
loadFingerCount
```

Example data includes:

```
ChamberNo          = 10
LoadDateJalali     = 1404-01-05
LoadTime           = 08:20
LoadOperatorCode   = 4
ProductCode        = 91000000
UnloadDateJalali   = 1404-01-09
UnloadTime         = 15:40
UnloadOperatorCode = 5
loadFingerCount    = 8
```

This dataset represents a dryer/chamber operation.

Potential analytical fields derived from this data include:

- chamber
- loading date
- loading time
- unloading date
- unloading time
- drying duration
- loading operator
- unloading operator
- product/mold
- finger count
- chamber utilization
- chamber cycle time
- operator performance
- drying throughput
- delayed unloading
- production waiting time

The system should calculate derived durations from canonical date/time values rather than storing redundant calculated values unless there is a justified performance reason.

---

## 8. DATASET B — WAGON / GLAZING / PACKAGING-STYLE TRANSITION DATA

The supplied table contains:

```
SettingID
wagon_no
GlazeType
start_time
end_time
packages
```

Examples include:

```
SettingID  = 1404010718
wagon_no   = 75
GlazeType  = 91000001
start_time = 06:25
end_time   = 07:25
packages   = 64
```

and:

```
SettingID  = 1404010718
wagon_no   = 41
GlazeType  = 91000001
start_time = 07:25
end_time   = 08:05
packages   = 64
```

This dataset demonstrates an important business relationship:

**One production setting / batch may be associated with multiple wagons.**

It also demonstrates that a wagon may be partially filled during a production operation.

For example:

```
Wagon 50    4 packages
+
Wagon 50    60 packages
=
64 packages
```

This means the final data model must NOT assume:

- One setting = one wagon

or:

- One wagon = one production record

Instead, relationships may be:

```
Production Setting
        ↓
Production Allocation
        ↓
Wagon
        ↓
Quantity / Packages
```

This is an important requirement for the future database design.

---

## 9. DATASET C — DRYER PRODUCTION / SHIFT / SUPERVISION DATA

The supplied table contains:

```
date_jalali
shift
supervisorID
OperatorCode_FK
personnel_count
chamber_no
productName
fingers_count
columns_count
dryer_waste
ID
```

Examples:

```
date_jalali     = 1404/1/7
shift           = 1
supervisorID    = 1
OperatorCode    = 9
personnel_count = 3
chamber_no      = 18
productName     = 91000000
fingers_count   = 7
columns_count   = 2
dryer_waste     = 150
ID              = 1404010718
```

This dataset provides evidence that production records can be associated with:

- Date
- Shift
- Supervisor
- Operator
- Personnel count
- Chamber
- Product / mold
- Finger count
- Column count
- Dryer waste

It also reveals an important data-quality issue:

**The same ID can occur more than once under different operational records.**

For example, the supplied data includes repeated IDs such as:

```
1404010913
1404011009
1404011404
1404011612
```

Therefore:

- The existing ID field MUST NOT automatically become the final database primary key.
- The migration design must determine the actual business key and distinguish duplicate operational records where necessary.

---

## 10. DATASET D — GRADING / QUALITY / WASTE DATA

The supplied table contains:

```
date_jalali
shift
OperatorCode_FK
typeOfWorkers
workerscount
productName
GlazeType
wagon_no
TotalCount
Grade1Count
WasteCount
```

Examples:

```
date_jalali  = 1404/01/04
shift        = 1
OperatorCode = 1
productName  = 91000000
GlazeType    = 91000001
wagon_no     = 75
TotalCount   = 1128
Grade1Count  = 1000
WasteCount   = 128
```

This is particularly important for analytics.

Basic yield can potentially be calculated as:

```
Grade 1 Yield % = Grade1Count / TotalCount × 100
```

Waste rate:

```
Waste Rate % = WasteCount / TotalCount × 100
```

But the system must not assume that:

```
TotalCount = Grade1Count + WasteCount
```

is always universally true.

The relationship must be validated against actual business rules because additional categories may exist in future, such as:

- Grade 2
- Rework
- Hold
- Broken
- Defective
- Unclassified
- Other

Therefore the future quality model should support multiple quality outcomes rather than hardcoding only Grade 1 and Waste.

---

## 11. REFERENCE DATA ALREADY PROVIDED

### 11.1 Supervisors

```
supervisorID | supervisors
1            | شاکر
2            | عموزاد
```

The final application should not rely on names as identifiers.

Use stable internal IDs.

---

## 12. OPERATORS

Existing operator mapping:

```
OperatorCode | Operator
4  | سید حسین جلالی
5  | وحید عموزاد
6  | عسگری قاسمی
8  | رجب علی پناه
7  | حسن یخکشی
9  | نصری
10 | علیپناه
11 | یخکشی
1  | علی پناه
2  | عموزاد
```

These names are historical reference data.

The final application must use a proper personnel model.

Potential structure:

```
Employee
    ↓
Employee Code
    ↓
Name
    ↓
Role
    ↓
Department
    ↓
Skills / Certifications
    ↓
Active / Inactive
```

Historical records must preserve the employee identity that existed at the time of production.

Employee changes must not corrupt historical analysis.

---

## 13. PRODUCT / MOLD REFERENCE DATA

Current mold mapping:

```
MoldID     | MoldsName | Internal Category
91000000   | طبرستان   | 1
92000000   | پرتغالی   | 2
81000000   | 20*10*20  | 3
```

The platform should eventually distinguish:

```
Product
Product Family
Product Category
Mold / Tool
Product Variant
Specification
```

The current field `productName` is sometimes effectively functioning as a mold/product identifier.

This must be resolved during data modeling.

---

## 14. GLAZE / PRODUCT TYPE REFERENCE DATA

Current type mapping:

```
91000001 | خودرنگ
91000002 | اخرا
91000003 | سبز
91000004 | نوک مدادی
91000005 | بیرنگ
91000006 | مشکی
91000007 | مولتی مشکی
91000008 | لعاب آزمایشی
92000001 | خودرنگ
92000002 | اخرا
92000003 | سبز
92000004 | نوک مدادی
92000005 | بیرنگ
92000006 | مشکی
92000007 | مولتی مشکی
92000008 | لعاب آزمایشی
93000001 | خودرنگ
93000002 | اخرا
93000003 | سبز
93000004 | نوک مدادی
93000005 | بیرنگ
93000006 | مشکی
93000007 | مولتی مشکی
93000008 | لعاب آزمایشی
```

This reveals that glaze/type codes are related to product/mold families.

The final system should not merely reproduce these codes.

A normalized structure should allow:

```
Product / Mold Family
        ↓
Finish / Glaze Type
        ↓
Product Variant
```

The historical code mapping must be retained so that old data remains interpretable.

---

## 15. PRODUCT CATEGORY DATA

Current categories:

```
1 | سفال
2 | تیزه
3 | پنجه ای
4 | نیمه
5 | آجر
```

These categories demonstrate that the initial plant already produces or tracks multiple product families.

The final system should allow administrators to define categories rather than hardcode these five values.

---

## 16. KNOWN PRODUCT DATA

The project has also supplied:

```
11000001 | سفال طبرستان خودرنگ
21000001 | تیزه طبرستان خودرنگ
31000001 | تیزه انتهایی طبرستان خودرنگ
53000001 | تیغه 20*10*20
```

These should become part of the historical migration mapping.

However, the final product model should support a richer structure:

```
Product Category
    ↓
Product Family
    ↓
Product
    ↓
Variant
    ↓
Finish / Glaze
    ↓
Mold / Tool
```

The exact hierarchy must be validated during domain modeling.

---

## 17. HISTORICAL DATA IS A CORE ASSET

This is one of the highest-priority requirements of the entire project.

The plant has at least approximately 15 years of historical production data.

This historical data must NOT be treated as disposable legacy Excel data.

It is a valuable manufacturing knowledge base.

The platform must support importing historical data from:

- Excel
- CSV
- potentially SQL/database exports
- other structured legacy sources

The migration system must support:

```
Raw Import → Staging → Mapping → Validation → Cleaning → Transformation → Deduplication → Normalization → Historical Database
```

---

## 18. HISTORICAL DATA MUST REMAIN TRACEABLE

Every imported historical record should ideally be traceable to:

```
Original File
Original Sheet
Original Row
Import Batch
Import Date
Mapping Version
Validation Status
Transformation History
```

This is essential because historical manufacturing data may contain inconsistencies.

We must never silently alter history.

If data is corrected, the system should preserve:

```
Original Value
Corrected Value
Reason
Who corrected it
When it was corrected
```

---

## 19. HISTORICAL DATA QUALITY

The existing data contains evidence of issues such as:

- duplicate IDs
- inconsistent date formatting
- Jalali date formats with different separators
- missing values
- partially populated fields
- operator-code ambiguity
- reused identifiers
- records representing different stages
- product/mold code ambiguity
- repeated wagon numbers
- potentially overlapping time records
- inconsistent terminology

These are NOT reasons to discard the data.

They are reasons to build a proper data migration and data-quality layer.

The migration process must classify problems such as:

```
Valid
Warning
Invalid
Duplicate
Needs Review
Mapped
Unmapped
```

---

## 20. JALALI / PERSIAN DATE SUPPORT

The historical data uses Persian/Jalali dates such as:

```
1404/01/04
1404/01/05
1404/01/09
```

and:

```
1404-01-05
```

The system must support Jalali dates in the user interface and import process.

Internally, the database should use a consistent canonical temporal representation suitable for calculations, sorting, querying, and integration.

The original historical date representation should remain recoverable where necessary.

The UI should support both:

- Jalali / Persian calendar
- Gregorian calendar

where appropriate.

---

## 21. HISTORICAL ANALYTICS

The system must support analysis across the entire available history.

Examples:

### Long-term production trends

```
Production by year
Production by month
Production by shift
Production by product
Production by category
```

### Long-term quality trends

```
Grade 1 %
Waste %
Waste by product
Waste by operator
Waste by supervisor
Waste by shift
Waste by machine
Waste by process stage
```

### Long-term productivity

```
Units / hour
Units / employee
Units / shift
Units / chamber
Units / wagon
```

### Historical process performance

```
Drying duration
Dryer throughput
Wagon loading time
Kiln cycle time
Production cycle time
Waiting time
```

---

## 22. HISTORY CHARTS

The platform must provide historical charts rather than only current dashboards.

Examples:

```
2011 ────────────────┐
2012 ────────────────┤
2013 ────────────────┤
...
2025 ────────────────┤
2026 ────────────────┘
```

Possible visualizations:

- Annual trends
- Monthly trends
- Weekly trends
- Shift comparisons
- Product trends
- Machine trends
- Operator trends
- Waste trends
- Yield trends
- Quality trends
- Production volume
- Cycle time
- Capacity utilization

Users should be able to select:

```
Date Range
Product
Category
Factory
Production Line
Machine
Shift
Operator
Supervisor
Process Stage
```

and compare historical periods.

---

## 23. BASELINE ANALYSIS

Historical data should be used to establish normal operating baselines.

For example:

```
Normal waste rate
Normal yield
Normal drying duration
Normal production/hour
Normal chamber utilization
Normal operator productivity
```

The system can then identify:

```
Current Result
vs
Historical Baseline
```

Example:

```
Current Waste Rate: 15.8%
Historical Normal Range: 9.5% – 12.2%
Status: Above historical baseline
```

This becomes much more useful than a simple static KPI.

---

## 24. STATISTICAL ANALYSIS

The analytics layer should eventually support:

- Mean
- Median
- Standard deviation
- Variance
- Percentiles
- Distribution analysis
- Control limits
- Correlation
- Regression
- Hypothesis testing
- ANOVA
- Pareto analysis
- Outlier detection
- Time-series analysis

The goal is to determine relationships such as:

```
Does drying duration affect waste?
Does operator affect waste?
Does shift affect yield?
Does product type affect quality?
Does chamber affect performance?
Does season affect drying?
Does production speed affect waste?
Does personnel count affect throughput?
Does mold/product combination affect quality?
```

These should be tested statistically rather than assumed.

---

## 25. MACHINE LEARNING

The 15+ years of historical data create a potential foundation for future machine-learning models.

Possible future models include:

### Waste prediction

Predict expected waste based on:

- product
- process
- operator
- shift
- chamber
- cycle time
- historical behavior
- production conditions

### Yield prediction

Predict expected Grade 1 percentage.

### Anomaly detection

Identify unusual production behavior.

### Forecasting

Predict:

- production
- demand
- waste
- quality
- throughput

### Recommendation engine

Eventually:

```
Expected waste is high.
Likely contributing factors:
1. Product X
2. Chamber Y
3. Short drying duration
4. Historical shift pattern
Recommended investigation:
Review drying cycle and chamber conditions.
```

AI-generated recommendations must always distinguish between:

```
Observed fact
Statistical relationship
Prediction
Hypothesis
Recommendation
```

The system must never present a statistical correlation as proven causation.

---

## 26. DATA LINEAGE

Every analytical result should eventually be traceable.

For example:

```
Dashboard KPI
     ↓
Analytics Calculation
     ↓
Filtered Dataset
     ↓
Production Records
     ↓
Original Imported Record
     ↓
Original Excel File / Sheet / Row
```

This is essential for industrial trust.

A manager should be able to ask:

**"Where did this number come from?"**

and the system should eventually be able to answer.

---

## 27. GENERIC MANUFACTURING PLATFORM

The final system must not contain assumptions such as:

```
Every factory has a dryer.
Every factory has a kiln.
Every factory uses wagons.
Every factory has fingers.
Every factory grades products as Grade 1.
```

Instead:

```
Equipment Type
Process Stage
Measurement
Quality Grade
Unit
Workflow
```

must be configurable.

---

## 28. INDUSTRY PACK CONCEPT

The platform may eventually support industry-specific templates.

For example:

```
Roof Tile Manufacturing Pack
Brick Manufacturing Pack
Ceramic Manufacturing Pack
Concrete Block Manufacturing Pack
```

An industry pack can provide:

- Default workflows
- Default product structures
- Default quality characteristics
- Default KPIs
- Default dashboards
- Default terminology
- Default reports

But customers must be able to customize them.

---

## 29. MULTI-FACTORY / MULTI-COMPANY

The platform architecture must be capable of supporting:

```
Company
    ↓
Factory
    ↓
Plant / Site
    ↓
Department
    ↓
Production Line
    ↓
Equipment
```

It must be possible for one customer to have multiple factories.

The first plant is only one implementation.

---

## 30. CONFIGURABILITY

Administrators should eventually be able to configure:

- Products
- Product categories
- Product variants
- Equipment
- Equipment types
- Production stages
- Workflows
- Shifts
- Employees
- Roles
- Quality grades
- Defect types
- Waste types
- Units
- KPIs
- Inspection forms
- Production parameters
- Dashboard widgets

without requiring code changes for normal configuration.

---

## 31. CORE DATA MODEL — CONCEPTUAL

The eventual domain model is expected to include concepts similar to:

```
Company
Factory
Plant
Department
ProductionLine
ProductCategory
ProductFamily
Product
ProductVariant
Mold
Recipe
Material
Glaze / Finish
Process
ProcessStage
Workflow
WorkflowStage
Operation
Machine
MachineType
Equipment
EquipmentEvent
WorkOrder
ProductionBatch
ProductionRun
ProductionOperation
Shift
Employee
Operator
Supervisor
Team
Chamber
Wagon
Tray
HandlingUnit
Inspection
QualityCharacteristic
QualityResult
Grade
Defect
Waste
Rework
ProductionMeasurement
MachineMeasurement
EnergyMeasurement
KPI
KPIDefinition
KPIResult
HistoricalImport
ImportBatch
ImportFile
ImportRow
DataMapping
DataQualityIssue
AuditLog
```

This is a conceptual list only.

It is NOT yet the final database schema.

---

## 32. DO NOT COPY THE EXCEL STRUCTURE DIRECTLY

This is a critical rule.

The existing Excel workbooks represent how the factory currently records information.

They do not necessarily represent the correct database design.

The final database must be designed from:

```
Business Domain
+
Real Factory Processes
+
Historical Data
+
Future Requirements
```

not:

```
Excel columns → database columns
```

---

## 33. DATA MIGRATION STRATEGY

Historical import should be treated as a dedicated subsystem.

Proposed pipeline:

```
                    Excel / CSV
                        │
                        ▼
                Import Manager
                        │
                        ▼
                  Raw Staging
                        │
                        ▼
                Data Profiling
                        │
                        ▼
                Mapping Engine
                        │
             ┌──────────┴─────────┐
             ▼                    ▼
        Valid Records       Data Issues
             │                    │
             ▼                    ▼
     Normalized Database     Review Queue
             │
             ▼
         Analytics
```

The application should eventually support previewing the import before committing it.

---

## 34. IMPORT FEATURES

The import system should eventually support:

- File upload
- Sheet selection
- Column mapping
- Data type detection
- Date conversion
- Code mapping
- Duplicate detection
- Missing-value detection
- Validation
- Preview
- Error report
- Import history
- Rollback where feasible
- Re-import
- Mapping templates

---

## 35. DATA QUALITY DASHBOARD

The platform should eventually have a data-quality dashboard showing:

```
Records Imported
Records Valid
Records With Warnings
Records Rejected
Duplicates
Missing Values
Unknown Codes
Invalid Dates
Unmapped Products
Unmapped Operators
```

This will be especially important for the 15+ year historical dataset.

---

## 36. ANALYTICS MUST NOT DESTROY OPERATIONAL DATA

Operational transactions and analytics should be logically separated.

Conceptually:

```
Operational Database
        ↓
Analytics / Reporting Layer
        ↓
Statistical Analysis
        ↓
ML Models
```

Analytics calculations should not modify historical operational records.

---

## 37. CURRENT DATA SHOULD BECOME A TEST DATASET

The supplied data should become a formal project asset.

We should eventually create:

```
/reference-data/
    operators
    supervisors
    products
    molds
    glaze-types
    categories
/sample-data/
    dryer
    wagon
    grading
/historical-data/
    imported source datasets
```

Sensitive production data must be handled according to the plant/customer's requirements.

---

## 38. KPI FRAMEWORK

The platform should eventually support configurable KPIs such as:

### Production

- Total production
- Good production
- Waste
- Yield
- Throughput
- Production/hour
- Production/employee

### Quality

- Grade 1 %
- Defect rate
- Waste rate
- Rework rate
- First-pass yield

### Equipment

- Utilization
- Availability
- Cycle time
- Downtime
- OEE where applicable

### Process

- Stage duration
- Waiting time
- Queue time
- Process efficiency
- Bottleneck analysis

### Workforce

- Productivity
- Output per employee
- Quality by operator
- Shift comparison

### Energy

Future support for:

- Fuel consumption
- Electricity
- Energy per unit
- Energy per batch
- Energy efficiency

---

## 39. HISTORICAL COMPARISON MUST BE BUILT INTO THE PLATFORM

The system should support comparisons such as:

```
Today vs Yesterday
This Week vs Last Week
This Month vs Last Month
This Year vs Last Year
Current Month vs Historical Average
Current Product vs Historical Product Performance
Current Shift vs Historical Shift Performance
Current Machine vs Historical Machine Performance
```

This is one of the major reasons the historical dataset is valuable.

---

## 40. PRODUCTION TRACEABILITY

Where the data permits, the system should eventually be able to trace:

```
Product
    ↓
Production Batch
    ↓
Process Stage
    ↓
Machine / Chamber
    ↓
Operator
    ↓
Shift
    ↓
Wagon / Handling Unit
    ↓
Quality Result
    ↓
Waste / Grade
```

This creates a digital production history.

---

## 41. REAL-TIME FUTURE

The initial system can work from manual entry and imported data.

Later it should be possible to integrate:

- PLC
- SCADA
- IoT sensors
- Machine counters
- Temperature sensors
- Energy meters
- Barcode scanners
- QR codes
- RFID
- weighing systems

The architecture should therefore remain API-first and integration-friendly.

---

## 42. APPLICATION USER ROLES

Potential roles include:

```
System Administrator
Company Administrator
Factory Manager
Production Manager
Supervisor
Operator
Quality Manager
Quality Inspector
Maintenance
Analyst
Management / Executive
```

Permissions must be role-based.

Users should only see the factories, departments, machines, and data they are authorized to access.

---

## 43. USER INTERFACE PRINCIPLE

The system must not look like a collection of database forms.

It should provide different experiences for different users.

### Operator

- Fast data entry.
- Minimal typing.
- Large controls.
- Touch-friendly.
- Clear workflow.

### Supervisor

- Shift monitoring.
- Exceptions.
- Production status.
- Quality.
- Waste.

### Manager

- KPIs.
- Trends.
- Comparisons.
- Bottlenecks.
- Alerts.

### Analyst

- Deep analysis.
- Filtering.
- Statistics.
- Exports.
- Historical data.

---

## 44. AI ASSISTANT RULES

Any AI used to develop or operate this platform must follow these rules:

- Never invent data.
- Never invent historical records.
- Never silently correct historical data.
- Never hardcode factory-specific assumptions into the generic platform.
- Never change the database schema without documenting the change.
- Never introduce a major architecture change without an Architecture Decision Record.
- Never claim statistical causation from correlation alone.
- Never delete historical records as part of cleaning.
- Never overwrite source data.
- Always preserve data lineage.
- Always explain assumptions.
- Always distinguish configuration from code.

---

## 45. DEVELOPMENT STACK — CURRENT DIRECTION

The current intended architecture is:

### Frontend

- React + TypeScript

### Backend

- Django + Django REST Framework

### Database

- PostgreSQL

### Cache / Background Infrastructure

- Redis
- Celery where background processing is required.

### Analytics

Python ecosystem, including:

- Pandas
- NumPy
- SciPy
- Scikit-learn

Additional ML libraries may be introduced later when justified.

### Deployment

- Linux/Ubuntu compatible.
- Containerized deployment is preferred.
- Docker should be considered part of the deployment architecture.
- Nginx can serve as the reverse proxy.

The architecture must remain suitable for on-premise factory deployment as well as future cloud deployment.

---

## 46. AI STUDIO DEVELOPMENT MODEL

Google AI Studio will be used as an implementation assistant, not as the owner of the architecture.

AI Studio must receive the project documentation before implementation.

Development should proceed in controlled phases:

```
Project Rules
      ↓
Product Requirements
      ↓
Domain Model
      ↓
Architecture
      ↓
Database
      ↓
API
      ↓
Backend
      ↓
Frontend
      ↓
Analytics
      ↓
Testing
      ↓
Deployment
```

AI Studio must not jump directly from a vague description to a complete production system.

---

## 47. DEVELOPMENT DOCUMENTATION ROADMAP

The project documentation should eventually contain:

```
00_MASTER_PROJECT_RULES.md
01_PROJECT_CHARTER.md
02_GLOSSARY.md
03_BUSINESS_DOMAIN_MODEL.md
04_BUSINESS_PROCESS_SPECIFICATION.md
05_FUNCTIONAL_REQUIREMENTS.md
06_NON_FUNCTIONAL_REQUIREMENTS.md
07_SYSTEM_ARCHITECTURE.md
08_DATABASE_DESIGN.md
09_API_SPECIFICATION.md
10_UI_UX_SPECIFICATION.md
11_ANALYTICS_SPECIFICATION.md
12_AI_ML_SPECIFICATION.md
13_DATA_MIGRATION_SPECIFICATION.md
14_SECURITY_SPECIFICATION.md
15_DEPLOYMENT_SPECIFICATION.md
16_TESTING_STRATEGY.md
17_ROADMAP.md
18_CODING_STANDARDS.md
```

Architecture decisions should additionally be stored under:

```
/adr/
```

---

## 48. DEVELOPMENT ORDER

The project must NOT begin by generating all application code.

The intended sequence is:

- **Phase 0** — Project Charter + Master Rules
- **Phase 1** — Glossary
- **Phase 2** — Business Domain Model
- **Phase 3** — Business Process Model
- **Phase 4** — Functional Requirements
- **Phase 5** — Non-Functional Requirements
- **Phase 6** — System Architecture
- **Phase 7** — Database + ERD
- **Phase 8** — Historical Data Migration Design
- **Phase 9** — API Design
- **Phase 10** — UI/UX
- **Phase 11** — Backend Implementation
- **Phase 12** — Frontend Implementation
- **Phase 13** — Analytics
- **Phase 14** — AI / ML
- **Phase 15** — Testing
- **Phase 16** — Deployment

---

## 49. MVP STRATEGY

The first release should focus on proving the platform architecture using the initial plant.

The MVP should include enough functionality to demonstrate:

```
Authentication
+
Master Data
+
Production Recording
+
Historical Import
+
Production History
+
Quality
+
Waste
+
Basic Dashboards
+
KPI Calculation
+
Historical Charts
```

It should NOT attempt to implement every advanced AI capability immediately.

The architecture must be ready for those capabilities, but they should be introduced after reliable data foundations are established.

---

## 50. HISTORICAL DATA FIRST-CLASS REQUIREMENT

The historical data must be considered part of the product from the beginning.

The platform is not:

```
New System
+
Old Data Archive
```

It is:

```
Historical Data
+
Current Data
+
Future Data
=
Manufacturing Knowledge Base
```

This knowledge base should become the foundation for:

- benchmarking
- trends
- forecasting
- predictive analytics
- anomaly detection
- process optimization
- management decisions
- continuous improvement

---

## 51. THE INITIAL FACTORY AS A LEARNING LAB

The first plant should be used to discover:

- Real manufacturing processes
- Data relationships
- Production constraints
- Quality patterns
- Historical trends
- Operational exceptions
- Data-quality problems
- Useful KPIs
- Useful analytics
- Practical user workflows

But we must distinguish:

**Factory-specific discovery**

from:

**Generic platform architecture**

A rule observed in the first plant must not automatically become a universal rule.

---

## 52. LONG-TERM PRODUCT VISION

The long-term platform should evolve toward:

```
                    Manufacturing Platform
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
     Execution            Analytics              AI
        │                    │                    │
        ▼                    ▼                    ▼
   Production          Historical BI        Prediction
   Quality             Statistics            Anomaly
   Workflow            Trends                Detection
   Equipment           Benchmarking          Recommendations
   Workforce           Correlation           Optimization
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    Manufacturing Intelligence
```

Eventually the system should progress from:

```
Record → Understand → Predict → Recommend → Optimize
```

---

## 53. NON-NEGOTIABLE REQUIREMENTS

The following requirements are considered foundational:

1. The application must be configurable for different manufacturing plants.
2. The application must not be hardcoded for one roof-tile factory.
3. The initial roof-tile factory remains the reference implementation.
4. Historical data of at least 15 years must be importable.
5. Historical data must remain queryable.
6. Historical data must support trend analysis.
7. Historical data must support charts.
8. Historical data must support statistical analysis.
9. Historical data must eventually support machine learning.
10. Existing Excel files must be importable.
11. Source data must not be destroyed during migration.
12. Historical records must preserve traceability.
13. Data cleaning must be auditable.
14. The platform must support multiple companies/factories.
15. Production workflows must be configurable.
16. Quality models must be configurable.
17. Products must be configurable.
18. Equipment must be configurable.
19. KPIs must be configurable wherever practical.
20. Analytics must be a first-class component.
21. The system must support historical/current/future data together.
22. The application must be designed for long-term extensibility.
23. The system must be API-first.
24. AI assistants must follow the project documentation.
25. Major architectural changes must be documented.

---

## 54. WHAT WE KNOW VS WHAT WE DO NOT YET KNOW

### Confirmed / Known

We currently have evidence of:

- Roof-tile / ceramic manufacturing.
- Dryer chambers.
- Dryer loading and unloading.
- Operators.
- Supervisors.
- Shifts.
- Personnel counts.
- Molds/products.
- Fingers.
- Columns.
- Dryer waste.
- Wagons.
- Glaze/finish types.
- Production settings.
- Packages.
- Grading.
- Grade 1 counts.
- Waste counts.
- Product categories.
- Historical Excel-style records.
- Jalali dates.
- At least approximately 15 years of historical data.
- A requirement for future multi-factory/multi-manufacturer support.

### Not Yet Fully Defined

We still need to investigate:

- Exact production workflow.
- Exact meaning of "finger".
- Exact meaning of "package".
- Exact meaning of "column".
- Exact relationship between mold, product, product variant, and glaze.
- Exact relationship between dryer records and wagon records.
- Exact relationship between wagon records and grading records.
- Exact kiln process.
- Kiln data currently available.
- Exact quality classification rules.
- Exact waste categories.
- Rework rules.
- Production batch definition.
- Work-order definition.
- Product recipes.
- Raw material data.
- Energy data.
- Maintenance data.
- Machine downtime data.
- IoT/PLC availability.
- Exact 15-year historical dataset structure.
- Existing Excel workbook inventory.
- Current business rules used by operators and supervisors.

These unknowns must be investigated before they become database assumptions.

---

## 55. THE MOST IMPORTANT ANALYTICAL OPPORTUNITY

The historical dataset should eventually allow us to move beyond simple reporting.

For example, we should investigate whether historical records reveal relationships between:

```
Product × Mold × Glaze × Chamber × Drying Duration × Operator × Shift × Personnel × Wagon × Production Quantity × Grade 1 × Waste
```

This could reveal hidden manufacturing relationships that are currently invisible when the information is separated across Excel workbooks.

The purpose of integrating the datasets is therefore not merely to eliminate Excel.

It is to create a connected manufacturing data model.

---

## 56. CENTRAL PROJECT IDEA

The central idea of the project is:

> **Turn fragmented manufacturing records into a connected, historical, configurable manufacturing knowledge system that helps factories understand performance, identify problems, predict outcomes, and improve production.**

- The first factory provides the real-world data and manufacturing knowledge.
- The platform architecture makes the solution reusable.
- The historical data provides the analytical foundation.
- The application provides operational execution and data collection.
- The analytics engine provides understanding.
- Machine learning provides prediction.
- AI eventually provides recommendations.

---

## 57. FINAL PROJECT PRINCIPLE

The project should always evolve according to this hierarchy:

```
REAL MANUFACTURING PROCESS
            ↓
DATA
            ↓
STRUCTURED INFORMATION
            ↓
ANALYTICS
            ↓
KNOWLEDGE
            ↓
PREDICTION
            ↓
DECISION SUPPORT
            ↓
CONTINUOUS IMPROVEMENT
```

The ultimate purpose of the platform is not to collect more data.

It is to convert manufacturing data into better manufacturing decisions.

---

## 58. CURRENT STATUS

At this point:

```
[✓] Product vision established
[✓] Generic multi-manufacturer requirement established
[✓] Initial factory identified
[✓] Existing data samples collected
[✓] Historical-data requirement established
[✓] Analytics-first principle established
[✓] AI/ML future direction established
[✓] Initial architecture direction established
[✓] Documentation strategy established
[ ] Final glossary
[ ] Detailed domain model
[ ] Detailed process model
[ ] Functional requirements
[ ] Non-functional requirements
[ ] Final architecture
[ ] ERD
[ ] Historical migration specification
[ ] API specification
[ ] UI/UX specification
[ ] Analytics specification
[ ] AI/ML specification
[ ] Implementation
```

Do not begin full application generation until the appropriate specifications have been approved.

---

## 59. NEXT DOCUMENT

The next document to create is:

**`02_GLOSSARY.md`**

It should formally define the project's manufacturing vocabulary.

The glossary should resolve ambiguous concepts discovered in the existing data, especially:

- Product
- Product Family
- Product Variant
- Mold
- Glaze
- Batch
- Work Order
- Production Run
- Production Setting
- Chamber
- Wagon
- Tray
- Finger
- Package
- Column
- Operation
- Process Stage
- Grade
- Waste
- Scrap
- Rework
- Yield
- Production Quantity
- Good Quantity
- Shift
- Operator
- Supervisor
- Personnel
- Equipment
- Cycle Time
- Drying Time
- Waiting Time

The glossary must be approved before the final domain model and database schema are created.

---

**END OF MASTER PROJECT RULES**
