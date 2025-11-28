---
description: "Data model and schema template for implementation planning"
---

# Data Model: [Feature Name]

**Feature**: [feature-id]
**Created**: [YYYY-MM-DD]
**Purpose**: Define data entities, relationships, and schema for implementation
**Source**: Derived from spec.md requirements and existing patterns

---

## Overview

**Summary**: [Brief description of the data model and its purpose]

**Key Entities**: [Entity1], [Entity2], [Entity3]

**Primary Relationships**:
- [Entity1] → [Entity2]: [relationship type]
- [Entity2] → [Entity3]: [relationship type]

---

## Entity Relationship Diagram (Text-Based)

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Entity1   │────────>│   Entity2   │────────>│   Entity3   │
│             │  1:many │             │  1:1    │             │
└─────────────┘         └─────────────┘         └─────────────┘
      │                        │
      │ 1:many                 │ 1:many
      ▼                        ▼
┌─────────────┐         ┌─────────────┐
│   Entity4   │         │   Entity5   │
└─────────────┘         └─────────────┘
```

**Legend**:
- `───>` : One-to-one relationship
- `═══>` : One-to-many relationship
- `<-->` : Many-to-many relationship

---

## Entity Definitions

### Entity 1: [EntityName]

**Purpose**: [What this entity represents and why it exists]

**Source**: [Requirement from spec.md or existing pattern at file:line]

#### Schema

| Field | Type | Constraints | Description | Source |
|-------|------|-------------|-------------|--------|
| `id` | UUID | PRIMARY KEY, NOT NULL | Unique identifier | Standard pattern |
| `[field1]` | [type] | [constraints] | [description] | [spec.md requirement or existing pattern] |
| `[field2]` | [type] | [constraints] | [description] | [spec.md requirement or existing pattern] |
| `[field3]` | [type] | [constraints] | [description] | [spec.md requirement or existing pattern] |
| `created_at` | timestamp | NOT NULL, DEFAULT NOW() | Record creation time | Standard pattern |
| `updated_at` | timestamp | NOT NULL, DEFAULT NOW() | Last update time | Standard pattern |

**Type Definitions** (if using TypeScript/similar):
```typescript
interface EntityName {
  id: string;  // UUID
  field1: FieldType;
  field2: FieldType;
  field3?: FieldType;  // Optional
  created_at: Date;
  updated_at: Date;
}

// Enums or union types if applicable
type FieldType = 'value1' | 'value2' | 'value3';
```

#### Constraints

**Uniqueness**:
- `field1` must be unique across all records
- Composite unique constraint: (`field2`, `field3`)

**Validation Rules**:
- `field1`: [validation rule, e.g., "must be valid email format"]
- `field2`: [validation rule, e.g., "must be between 1-100 characters"]
- `field3`: [validation rule, e.g., "must be positive integer"]

**Foreign Keys**:
- `entity2_id` → Entity2.id (CASCADE on delete)
- `entity3_id` → Entity3.id (SET NULL on delete)

**Check Constraints**:
- `field1 > 0` (business rule from spec.md)
- `field2 IN ('status1', 'status2', 'status3')`

#### Indexes

```sql
-- Performance optimization based on query patterns
CREATE INDEX idx_entity1_field1 ON entity1(field1);
CREATE INDEX idx_entity1_field2_field3 ON entity1(field2, field3);
CREATE INDEX idx_entity1_created_at ON entity1(created_at);

-- Full-text search (if applicable)
CREATE INDEX idx_entity1_search ON entity1 USING GIN(to_tsvector('english', field1));
```

**Rationale**:
- `idx_entity1_field1`: Supports lookup by field1 (common query pattern at file:line)
- `idx_entity1_field2_field3`: Supports composite queries (required by spec.md FR-001)
- `idx_entity1_created_at`: Supports time-based filtering (pagination requirement)

#### Relationships

**Outbound** (this entity references others):
- `Entity2`: Many-to-one relationship via `entity2_id`
  - **Constraint**: CASCADE on delete (if Entity2 deleted, this entity also deleted)
  - **Rationale**: [Business rule from spec.md]

**Inbound** (others reference this entity):
- `Entity4`: One-to-many relationship (Entity4 has foreign key to this entity)
  - **Constraint**: RESTRICT on delete (cannot delete this if Entity4 records exist)
  - **Rationale**: [Business rule from spec.md]

**Many-to-Many**:
- `Entity5`: Through junction table `entity1_entity5`
  - **Junction Fields**: `entity1_id`, `entity5_id`, `created_at`
  - **Rationale**: [Business rule from spec.md]

#### Example Data

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field1": "example value",
  "field2": "status1",
  "field3": 42,
  "entity2_id": "660e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

#### Migrations

**Initial Creation**:
```sql
CREATE TABLE entity1 (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  field1 VARCHAR(255) NOT NULL UNIQUE,
  field2 VARCHAR(50) NOT NULL CHECK (field2 IN ('status1', 'status2', 'status3')),
  field3 INTEGER CHECK (field3 > 0),
  entity2_id UUID REFERENCES entity2(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_entity1_field1 ON entity1(field1);
CREATE INDEX idx_entity1_created_at ON entity1(created_at);

-- Triggers
CREATE TRIGGER update_entity1_updated_at
  BEFORE UPDATE ON entity1
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

**Evolution** (if schema changes):
- [Version 2]: Add `field4` column for [requirement]
- [Version 3]: Add index on `field2` for [performance optimization]

---

### Entity 2: [EntityName]

[Same structure as Entity 1]

---

### Entity 3: [EntityName]

[Same structure as Entity 1]

---

[Add more entities as needed]

---

## Junction Tables (Many-to-Many Relationships)

### Table: [entity1_entity2]

**Purpose**: Links Entity1 and Entity2 in many-to-many relationship

**Requirement**: [spec.md requirement that necessitates this relationship]

#### Schema

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `entity1_id` | UUID | NOT NULL, FOREIGN KEY | Reference to Entity1 |
| `entity2_id` | UUID | NOT NULL, FOREIGN KEY | Reference to Entity2 |
| `created_at` | timestamp | NOT NULL, DEFAULT NOW() | When relationship created |
| `metadata` | JSONB | NULL | Optional relationship metadata |

**Primary Key**: Composite (`entity1_id`, `entity2_id`)

**Constraints**:
```sql
ALTER TABLE entity1_entity2
  ADD CONSTRAINT pk_entity1_entity2
    PRIMARY KEY (entity1_id, entity2_id);

ALTER TABLE entity1_entity2
  ADD CONSTRAINT fk_entity1
    FOREIGN KEY (entity1_id) REFERENCES entity1(id) ON DELETE CASCADE;

ALTER TABLE entity1_entity2
  ADD CONSTRAINT fk_entity2
    FOREIGN KEY (entity2_id) REFERENCES entity2(id) ON DELETE CASCADE;
```

---

## Data Access Patterns

### Pattern 1: [Pattern Name]

**Use Case**: [What operation this supports, from spec.md]

**Query**:
```sql
SELECT e1.*, e2.field1
FROM entity1 e1
JOIN entity2 e2 ON e1.entity2_id = e2.id
WHERE e1.field1 = $1
  AND e1.created_at > $2
ORDER BY e1.created_at DESC
LIMIT 20;
```

**Indexes Used**:
- `idx_entity1_field1` (for WHERE clause)
- `idx_entity1_created_at` (for ORDER BY)

**Performance Target**: [< 50ms for p95, from spec.md NFR-001]

**Existing Pattern**: Found at `[file:line]` (similar query pattern)

---

### Pattern 2: [Pattern Name]

[Same structure as Pattern 1]

---

[Add more patterns as needed]

---

## Data Lifecycle & State Management

### Entity1 State Transitions

```
[Initial State] → [State 1] → [State 2] → [Final State]
                     ↓            ↓
                [Error State] [Error State]
```

**State Definitions**:
- **Initial State**: [description]
- **State 1**: [description]
- **State 2**: [description]
- **Final State**: [description]
- **Error State**: [description]

**Valid Transitions**:
| From | To | Trigger | Validation |
|------|----|----|---------|
| Initial | State1 | [Action] | [Condition that must be true] |
| State1 | State2 | [Action] | [Condition that must be true] |
| State2 | Final | [Action] | [Condition that must be true] |

**Business Rules** (from spec.md):
- [Rule 1]: [Description]
- [Rule 2]: [Description]

---

## Data Validation Rules

### Field-Level Validation

**Entity1**:
- `field1`: [Validation rule with example]
- `field2`: [Validation rule with example]
- `field3`: [Validation rule with example]

**Entity2**:
- [Same structure]

### Business Rule Validation

**Cross-Field Rules**:
1. **Rule 1**: If `field1` is [value], then `field2` must be [value]
   - **Source**: spec.md requirement FR-005
   - **Implementation**: [Check constraint or application logic]

2. **Rule 2**: [Description]
   - **Source**: [spec.md reference]
   - **Implementation**: [How enforced]

**Cross-Entity Rules**:
1. **Rule 1**: An Entity1 can only reference Entity2 if Entity2.status is 'active'
   - **Source**: spec.md requirement FR-008
   - **Implementation**: [Trigger or application logic]

---

## Security & Access Control

### Row-Level Security (RLS)

**Entity1 Policies**:
```sql
-- Users can only see their own records
CREATE POLICY entity1_select_policy ON entity1
  FOR SELECT
  USING (user_id = current_user_id());

-- Users can only update their own records
CREATE POLICY entity1_update_policy ON entity1
  FOR UPDATE
  USING (user_id = current_user_id());
```

**Rationale**: [Security requirement from spec.md NFR-SEC-001]

### Data Sensitivity Classification

| Entity | Classification | PII | Encryption Required | Audit Required |
|--------|---------------|-----|---------------------|----------------|
| Entity1 | Confidential | Yes (field1, field2) | At-rest + In-transit | Yes |
| Entity2 | Internal | No | In-transit only | No |
| Entity3 | Public | No | In-transit only | No |

**Compliance**: [GDPR / CCPA / HIPAA requirements from spec.md]

---

## Data Retention & Archival

### Retention Policies

**Entity1**:
- **Active Records**: Keep indefinitely
- **Soft-Deleted Records**: Keep for 90 days, then hard delete
- **Rationale**: [Business requirement from spec.md]

**Entity2**:
- **All Records**: Keep for 7 years (compliance requirement)
- **Archive After**: 2 years to cold storage
- **Rationale**: [Legal/compliance requirement]

### Soft Delete Pattern

```sql
-- Add deleted_at column
ALTER TABLE entity1 ADD COLUMN deleted_at TIMESTAMP NULL;

-- Create index for active records query
CREATE INDEX idx_entity1_active ON entity1(id) WHERE deleted_at IS NULL;

-- Soft delete query
UPDATE entity1 SET deleted_at = NOW() WHERE id = $1;

-- Query active records only
SELECT * FROM entity1 WHERE deleted_at IS NULL;
```

**Cleanup Job**:
```sql
-- Delete records soft-deleted > 90 days ago
DELETE FROM entity1
WHERE deleted_at IS NOT NULL
  AND deleted_at < NOW() - INTERVAL '90 days';
```

---

## Performance Optimization

### Query Optimization

**Slow Query Candidates** (based on requirements):
1. **Query**: [Description of potentially slow query]
   - **Optimization**: [Index, partitioning, materialized view, etc.]
   - **Expected Improvement**: [X ms → Y ms]

2. **Query**: [Description]
   - **Optimization**: [Strategy]
   - **Expected Improvement**: [Metric]

### Caching Strategy

**Entity1**:
- **Cache**: Frequently accessed records (read-heavy operations)
- **TTL**: 5 minutes
- **Invalidation**: On update or delete
- **Rationale**: [Performance requirement from spec.md NFR-002]

**Entity2**:
- **No caching**: Write-heavy, real-time requirements
- **Rationale**: [Consistency requirement from spec.md]

### Partitioning Strategy (if applicable)

**Entity1 Partitioning**:
- **Method**: Range partitioning by `created_at`
- **Partition Size**: Monthly
- **Rationale**: [Data volume from spec.md, query patterns]

```sql
-- Create partitioned table
CREATE TABLE entity1 (
  id UUID,
  field1 VARCHAR(255),
  created_at TIMESTAMP NOT NULL,
  ...
) PARTITION BY RANGE (created_at);

-- Create partitions
CREATE TABLE entity1_2025_01 PARTITION OF entity1
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE entity1_2025_02 PARTITION OF entity1
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

---

## Scaling Considerations

### Vertical Scaling Limits

**Entity1**:
- **Estimated Rows**: [X million] (based on spec.md requirements)
- **Growth Rate**: [Y% per month]
- **Single Server Limit**: [Z million rows or N GB]

**When to Consider Horizontal Scaling**: [Threshold and indicators]

### Horizontal Scaling Strategy

**Read Scaling**:
- **Read Replicas**: [Number] for read-heavy operations
- **Load Balancer**: Route reads to replicas, writes to primary
- **Rationale**: [Scalability requirement from spec.md NFR-003]

**Write Scaling** (if needed):
- **Sharding Strategy**: [Shard key, shard count]
- **Shard Key**: `field1` (ensures even distribution)
- **Rationale**: [Scale requirement from spec.md]

---

## Data Migration Strategy

### From Existing Schema (if applicable)

**Current Schema**: [Description of existing schema at file:line]

**Migration Steps**:
1. **Create new tables** (parallel to existing)
2. **Backfill data** using migration script
3. **Run dual-write** to both old and new schemas
4. **Verify data consistency**
5. **Switch read path** to new schema
6. **Remove old schema** after validation period

**Rollback Plan**: [How to revert if issues found]

### Initial Data Seeding

**Required Seed Data**:
- **Entity1**: [Description of seed data needed]
- **Entity2**: [Description of seed data needed]

**Seed Script** (pseudocode):
```sql
INSERT INTO entity2 (field1, field2) VALUES
  ('value1', 'value2'),
  ('value3', 'value4');

INSERT INTO entity1 (field1, entity2_id) VALUES
  ('value', (SELECT id FROM entity2 WHERE field1 = 'value1'));
```

---

## Testing Strategy

### Unit Tests (Schema Validation)

**Test Cases**:
1. **Test constraint enforcement**: Verify CHECK constraints reject invalid data
2. **Test foreign key cascades**: Verify CASCADE/RESTRICT behavior
3. **Test uniqueness constraints**: Verify UNIQUE constraints work
4. **Test default values**: Verify DEFAULT expressions work

### Integration Tests (Data Access Patterns)

**Test Cases**:
1. **Test query pattern 1**: Verify performance meets target
2. **Test query pattern 2**: Verify correct results
3. **Test relationship queries**: Verify JOINs work correctly

### Data Migration Tests (if applicable)

**Test Cases**:
1. **Test data consistency**: Verify all data migrated correctly
2. **Test referential integrity**: Verify foreign keys maintained
3. **Test rollback**: Verify ability to revert migration

---

## CoD^Σ Evidence Trail

### Requirements → Schema Mapping

| Requirement (spec.md) | Entity | Field/Constraint | Justification |
|----------------------|--------|------------------|---------------|
| FR-001: [requirement] | Entity1 | field1 (UNIQUE) | [Why this design choice] |
| FR-002: [requirement] | Entity1 | field2 (CHECK) | [Why this constraint] |
| NFR-001: [performance] | Entity1 | idx_entity1_field1 | [Why this index] |

### Existing Pattern Evidence

| Pattern | Location | Adopted/Adapted | Rationale |
|---------|----------|----------------|-----------|
| UUID primary keys | `[file:line]` | Adopted | Standard across codebase |
| Timestamp tracking | `[file:line]` | Adopted | Standard audit trail |
| Soft delete pattern | `[file:line]` | Adopted | Consistent deletion approach |

---

## Open Questions

**Schema Questions**:
1. [Question 1]: [Why clarification needed]
   - **Impact**: [High/Medium/Low]
   - **Blocking**: [Yes/No]

2. [Question 2]: [Why clarification needed]
   - **Impact**: [High/Medium/Low]
   - **Blocking**: [Yes/No]

**Performance Questions**:
1. [Question 1]: [What needs validation/benchmarking]

---

## References

### Existing Schema References (via project-intel.mjs)
- `[file:line]` - [Entity definition or migration]
- `[file:line]` - [Query pattern]

### External Documentation (via MCP)
- [Database documentation URL]
- [ORM documentation URL]

---

**Data Model Version**: 1.0
**Next Review**: After spec clarification or during implementation
**Status**: [Draft / Under Review / Approved]
