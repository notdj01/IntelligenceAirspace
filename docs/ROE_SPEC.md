# Legal-Agentic Co-Pilot (ROE Specialist) Specification

## Overview

**Feature Name:** LLM-Driven Rules of Engagement (ROE) Specialist  
**Type:** Agentic AI Node for Airspace Monitoring System  
**Core Functionality:** Provides legally-grounded response recommendations based on airspace regulations (DGCA/FAA), zone classifications, and threat assessment.  
**Target Users:** Air traffic operators, security personnel, drone defense system operators

---

## Problem Statement

Operators often hesitate during critical moments because they don't know the legal protocols for responding to aerial threats in specific zones. This hesitation can lead to:
- Delayed responses to genuine threats
- Illegal actions taken without proper authorization
- Liability issues from improper countermeasure deployment

---

## Solution: Legal-Agentic Co-Pilot

A RAG (Retrieval-Augmented Generation) based agent that:
1. Memorizes airspace regulations (DGCA India, FAA USA, EASA Europe)
2. Knows zone-specific restrictions (No-Fly Zones, Restricted Areas, Temporary Flight Restrictions)
3. Provides context-aware legal recommendations for each threat

---

## Key Features

### 1. Zone-Based Response Matrix
| Zone Type | Threat Type | Allowed Responses |
|-----------|-------------|-------------------|
| Residential (Zone A) | Unauthorized Drone | RF Jam (non-kinetic only), Digital Honeypot |
| Critical Infrastructure | Hostile/Drone | RF Jam, Geo-fence enforcement |
| Airports (Zone C) | Any | Coordinate with ATC, Visual verification |
| Military Base | Unknown | Full defensive measures authorized |
| Temporary Restricted | Unauthorized | Warning + forced landing command |

### 2. Regulation Knowledge Base

**DGCA (India) - Civil Aviation Requirements:**
- CAR Section 3: Airspace Regulations
- CAR Section 4: Unmanned Aircraft System Rules
- Digital Sky Platform guidelines

**FAA (USA):**
- Part 107: Small UAS Rules
- Part 109: Operation of Small UAS
- AIRSPACE Authorizations

**Response Protocols:**
- Section 4.2: RF Jamming Protocol Alpha-7
- Section 4.3: Kinetic Interdiction Prohibited Zones
- Section 5.1: Emergency Authorizations

### 3. RAG-Based Legal Reasoning

The agent will:
1. Retrieve relevant regulations based on:
   - Current zone (NFZ type, TFR status)
   - Threat classification (drone, spoofed aircraft, unidentified)
   - Risk level (Low, Medium, High, Critical)
   - Time of day (day/night restrictions)
   
2. Generate recommendation including:
   - Legal basis (CAR section / FAR reference)
   - Authorized countermeasures
   - Reporting requirements
   - Liability notes

---

## Technical Architecture

### Data Flow
```
Target (risk_assessment) 
    → ROE Agent (Legal Co-Pilot)
        → Lookup zone type
        → Retrieve applicable regulations
        → Generate recommendation
    → Final Response + Legal Justification
```

### Files to Create/Modify

1. **New Files:**
   - `agents/roe_node.py` - ROE agent implementation
   - `data/regulations.json` - Knowledge base
   - `data/zone_rules.json` - Zone-specific rules

2. **Modify:**
   - `agents/state.py` - Add ROE fields to TargetMetadata
   - `agents/graph.py` - Add roe_node to pipeline
   - `Frontend/src/app/components/roe-panel.tsx` - New UI component

---

## Implementation Details

### ROE Recommendation Output Structure
```python
@dataclass
class ROERecommendation:
    zone_type: str                    # "Residential", "Critical", "Airport", etc.
    threat_level: str                 # Based on classification
    authorized_response: List[str]    # e.g., ["RF Jam", "Honeypot"]
    prohibited_response: List[str]   # e.g., ["Kinetic Interdiction"]
    legal_basis: str                  # e.g., "CAR Section 4.2"
    reporting_required: bool          # Whether to file report
    liability_note: str               # Any liability warnings
    confidence: float                 # 0.0 - 1.0
```

### Zone Classification Logic
1. Check distance to defined NoFlyZones
2. Determine zone type (Permanent NFZ, TFR, Restricted, Open)
3. Apply zone-specific response matrix
4. Generate legally-compliant recommendation

---

## UI Integration

### Commander XAI Panel (Existing)
Add ROE section showing:
- **Zone:** Current zone classification
- **Legal Basis:** Applicable regulation
- **Recommended Action:** Prioritized list
- **Prohibited Actions:** What NOT to do

### Visual Indicators
- Green badge: Full defensive measures authorized
- Yellow badge: Limited response (non-kinetic only)
- Red badge: No response - coordinate with authorities

---

## Success Criteria

1. **Accuracy:** 100% of recommendations cite valid regulation references
2. **Coverage:** All defined NoFlyZones have response matrices
3. **Latency:** < 100ms per recommendation (non-LLM fallback)
4. **Safety:** No recommendations for prohibited actions in restricted zones

---

## Future Enhancements

1. **Live Regulation Updates:** Connect to DGCA/FAA APIs for real-time updates
2. **Multi-Jurisdiction:** Support for more countries (UK CAA, EASA, etc.)
3. **Natural Language Queries:** Operator can ask "Can I jam this drone in Delhi?"
4. **Audit Trail:** Full logging of recommendations for legal proceedings
