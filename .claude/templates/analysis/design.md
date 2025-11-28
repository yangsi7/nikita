# Feature Design: {{feature_name}}

**Generated**: {{timestamp}}
**Mode**: Feature Analysis
**Target**: {{feature_name}}
**Analyst**: Claude Code Intelligence Toolkit
**Token Cost**: {{token_cost}} ({{savings_percentage}}% savings vs direct reading)

---

## Executive Summary

{{executive_summary}}

**Feature Scope**: {{feature_scope_summary}}
**Complexity Rating**: {{complexity_rating}} (Simple/Medium/Complex)
**Modification Risk**: {{modification_risk}} (Low/Medium/High)

---

## Feature Boundary

### Files in Scope ({{file_count}})

{{feature_files_table}}

**Boundary Definition**:
{{boundary_explanation}}

**Related but Out-of-Scope**:
{{related_files_out_of_scope}}

---

## Entry Point

**Main File**: `{{entry_point_file}}`
**Main Component/Function**: `{{entry_point_symbol}}` (line {{entry_point_line}})

{{entry_point_description}}

**Invocation Path**:
```
{{invocation_path}}
```

---

## Component Hierarchy

```mermaid
graph TD
{{component_hierarchy_mermaid}}
```

**Component Relationships**:
{{component_relationships_explanation}}

---

## Dependency Graph

### Upstream Dependencies (What This Feature Imports)

```mermaid
graph LR
{{upstream_dependencies_mermaid}}
```

{{upstream_dependencies_table}}

**External Dependencies**:
{{external_dependencies_list}}

### Downstream Dependencies (What Imports This Feature)

```mermaid
graph LR
{{downstream_dependencies_mermaid}}
```

{{downstream_dependencies_table}}

**Impact Analysis**: Modifying this feature affects {{downstream_count}} consumers

---

## Data Flow

### State Management

{{state_management_description}}

**State Variables**:
{{state_variables_table}}

**State Flow**:
```
{{state_flow_diagram}}
```

### API Interactions

{{api_interactions_description}}

**API Calls**:
{{api_calls_table}}

**Data Transformation Flow**:
```
{{data_transformation_diagram}}
```

---

## Key Functions & Types

### Exported Functions

{{exported_functions_table}}

### Exported Types

{{exported_types_table}}

### Internal Utilities

{{internal_utilities_table}}

---

## Integration Points

### External Systems

{{external_systems_list}}

**Integration Details**:
{{integration_details_table}}

### Shared Utilities

{{shared_utilities_list}}

**Usage Pattern**:
{{shared_utilities_pattern}}

### Event Handling

{{event_handlers_list}}

**Event Flow**:
```
{{event_flow_diagram}}
```

---

## Code Excerpts (Key Sections)

### Main Implementation

**File**: `{{main_impl_file}}`
**Lines**: {{main_impl_start}}-{{main_impl_end}}

```{{main_impl_language}}
{{main_impl_code}}
```

**Analysis**:
{{main_impl_analysis}}

### Hook/Utility Logic

**File**: `{{hook_file}}`
**Lines**: {{hook_start}}-{{hook_end}}

```{{hook_language}}
{{hook_code}}
```

**Analysis**:
{{hook_analysis}}

---

## Testing Coverage

**Test Files**: {{test_file_count}}
**Test Coverage**: {{test_coverage_percentage}}%

{{test_files_list}}

**Coverage Gaps**:
{{coverage_gaps_list}}

---

## Performance Considerations

{{performance_analysis}}

**Optimization Opportunities**:
{{optimization_opportunities}}

**Known Performance Issues**:
{{known_performance_issues}}

---

## Security Considerations

{{security_analysis}}

**Security Checklist**:
{{security_checklist}}

---

## Modification Guide

### How to Extend This Feature

{{extension_guide}}

### How to Modify Behavior

{{modification_guide}}

### Breaking Change Checklist

{{breaking_change_checklist}}

---

## Common Issues & Gotchas

{{common_issues_list}}

**Debugging Tips**:
{{debugging_tips}}

---

## Related Features

{{related_features_list}}

**Integration Points**:
{{related_features_integration}}

---

## Recommendations

### For Understanding
{{understanding_recommendations}}

### For Development
{{development_recommendations}}

### For Testing
{{testing_recommendations}}

### For Refactoring
{{refactoring_recommendations}}

---

## Evidence Chain (CoD^Σ)

### Intelligence Queries Executed

```
{{intelligence_queries_cod}}
```

**Query Results Summary**:
- Search Results: {{search_result_count}} files found
- Entry Point Identified: {{entry_point_file}}
- Components Analyzed: {{components_analyzed_count}}
- Dependencies Traced: {{dependencies_traced_count}}

**Targeted Reads** (vs full file reading):
{{targeted_reads_summary}}

**Total Token Usage**:
- Intel Queries: {{intel_tokens}} tokens
- Targeted Reads: {{read_tokens}} tokens
- MCP Verification: {{mcp_tokens}} tokens
- Processing: {{processing_tokens}} tokens
- Output: {{output_tokens}} tokens
- **Total**: {{total_tokens}} tokens

**vs. Reading All Feature Files**: {{baseline_tokens}} tokens
**Savings**: {{savings_percentage}}%

---

## Appendix A: Symbol Export Map

{{symbol_export_map}}

---

## Appendix B: Dependency Matrix

{{dependency_matrix}}

---

## Appendix C: File Change History

{{file_change_history}}

---

**Reference**: This feature context should be referenced in `CLAUDE.md` as:

```markdown
## Reference Inventory

- **@refs/design.md** - {{feature_name}} feature context (generated {{timestamp}})
```

**Regenerate When**:
- Feature functionality changes
- New sub-features added
- Integration points modified
- Major refactoring occurs

---

**Generated by**: analyze-code skill (feature mode)
**Workflow**: @.claude/skills/analyze-code/workflows/feature-workflow.md
**Intelligence Tool**: @.claude/shared-imports/project-intel-mjs-guide.md
