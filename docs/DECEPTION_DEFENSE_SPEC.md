# Agentic "Honeypot" Airspace - Deceptive Defense Feature

## Technical Specification

### Overview
This feature implements an Active Deception Engine that provides autonomous counter-drone capabilities through GPS spoofing and digital honeypot luring. When an unidentified or hostile drone enters restricted airspace, the system doesn't just alert operators—it actively redirects the threat to a safe "Cyber-Catcher" zone.

### Core Components

#### 1. Cyber-Catcher Zones
Pre-designated safe landing zones where deceptive lures direct hostile drones:
- **Location**: Configurable empty/safe areas within operational region
- **Properties**: Latitude, Longitude, Radius (meters), Safety rating

#### 2. Synthetic Meaconing Signals
Fake GPS signals broadcast to mislead drone navigation:
- **Approach**: Gradually shift apparent GPS position toward Cyber-Catcher
- **Algorithm**: Bezier curve interpolation for natural-looking deviation
- **Frequency**: L1 (1575.42 MHz) GPS band simulation

#### 3. Digital Honeypot
Fake WiFi/control access points to attract drones:
- **SSIDs**: Common drone manufacturer patterns (DJI-XXXX, Phantom-XXXX)
- **Protocols**: MAVLink, DJI WiFi protocols simulation
- **Purpose**: Capture or redirect autonomous drones

### Architecture

```
Detection → Classification → Risk Assessment → ROE → DECEPTION_ENGINE → Response
```

### State Extensions

New fields in TargetMetadata:
- `deception_active`: bool - Is deception currently being applied
- `deception_type`: str - Type of deception (GPS_SPOOF, HONEYPOT, HYBRID)
- `cyber_catcher_target`: dict - Target coordinates for lure
- `deception_start_time`: float - Unix timestamp when deception started
- `deception_technique`: str - Specific technique being used

### Integration with Existing ROE

The deception engine integrates with the existing Rules of Engagement system:

| Zone Type | GPS_SPOOF | HONEYPOT | RF_JAM |
|-----------|-----------|----------|--------|
| PROHIBITED | ✅ | ✅ | ✅ |
| CRITICAL_INFRA | ✅ | ✅ | ✅ |
| RESTRICTED | ✅ | ✅ | ✅ |
| RESIDENTIAL | ❌ | ✅ | ❌ |
| AIRPORT_5KM | ❌ | ❌ | ❌ |
| OPEN | ❌ | ❌ | ❌ |

### Implementation Phases

1. **Phase 1**: State model extensions for deception tracking
2. **Phase 2**: Cyber-Catcher zone management
3. **Phase 3**: Deception decision engine (DeceptionNode)
4. **Phase 4**: Signal generation logic (simulation)
5. **Phase 5**: Pipeline integration

### Security Considerations

- **Authorization Required**: Deception only activates for authorized zones per ROE
- **Fail-safe**: Automatic deactivation if drone enters unintended area
- **Logging**: Full audit trail of all deception operations
- **Human-in-loop**: Optional operator approval for critical zone deployments
