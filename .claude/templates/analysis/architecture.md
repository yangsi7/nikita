# Architecture Analysis: {{project_name}}

**Generated**: {{timestamp}}
**Mode**: Architecture Analysis
**Analyst**: Claude Code Intelligence Toolkit
**Token Cost**: {{token_cost}} ({{savings_percentage}}% savings vs direct reading)

---

## Executive Summary

{{executive_summary}}

**Architecture Health**: {{architecture_health_rating}} (Excellent/Good/Fair/Poor)
**Critical Issues**: {{critical_issues_count}}
**Recommendations**: {{recommendations_count}}

---

## Architecture Overview

{{architecture_overview_description}}

**Architectural Style**: {{architectural_style}} (e.g., Layered, Hexagonal, Clean Architecture)
**Patterns Used**: {{patterns_used_list}}

---

## Layer Structure

### Detected Layers

```mermaid
graph TD
{{layers_mermaid_diagram}}
```

{{layers_table}}

**Layer Descriptions**:
{{layer_descriptions}}

---

## Layer Boundaries & Rules

### Boundary Rules

{{boundary_rules_table}}

**Enforcement**:
{{boundary_enforcement_description}}

**Allowed Dependencies**:
```
{{allowed_dependencies_diagram}}
```

---

## Boundary Violations

### Critical Violations ({{critical_violations_count}})

{{critical_violations_table}}

### Warning-Level Violations ({{warning_violations_count}})

{{warning_violations_table}}

**Violation Analysis**:
{{violation_analysis}}

**Impact Assessment**:
{{violation_impact}}

---

## Circular Dependencies

### Cycles Detected ({{cycles_count}})

{{cycles_table}}

**Cycle Diagrams**:
```mermaid
graph LR
{{cycles_mermaid}}
```

**Resolution Recommendations**:
{{cycle_resolution_recommendations}}

---

## Architectural Patterns

### Primary Patterns

{{primary_patterns_table}}

**Pattern Details**:
{{pattern_details}}

### Design Patterns Identified

{{design_patterns_table}}

**Pattern Usage Analysis**:
{{pattern_usage_analysis}}

---

## Component Coupling

### Highly Coupled Modules ({{high_coupling_count}})

{{high_coupling_table}}

**Coupling Metrics**:
- Average Afferent Coupling: {{avg_afferent}}
- Average Efferent Coupling: {{avg_efferent}}
- Instability (I): {{instability_metric}}
- Abstractness (A): {{abstractness_metric}}

**Coupling Heatmap**:
{{coupling_heatmap}}

---

## Code Quality Metrics

### Complexity Analysis

{{complexity_analysis_table}}

**Complexity Distribution**:
{{complexity_distribution_chart}}

**Refactoring Candidates** (Complexity > 10):
{{refactoring_candidates_table}}

### Dead Code Detection

**Dead Code Found**: {{dead_code_count}} files/functions
**Potential Savings**: {{dead_code_savings}} LOC

{{dead_code_table}}

### TypeScript Usage

**TypeScript Coverage**: {{typescript_coverage}}%
**Any Type Usage**: {{any_type_count}} instances

{{typescript_analysis}}

---

## Dependency Analysis

### Import Graph Statistics

{{import_graph_stats}}

**Most Imported Modules** (High Coupling Risk):
{{most_imported_modules_table}}

**Least Reused Modules** (Potential Dead Code):
{{least_reused_modules_table}}

### External Dependencies

**Production Dependencies**: {{prod_deps_count}}
**Dev Dependencies**: {{dev_deps_count}}

{{external_dependencies_risk_table}}

**Outdated Dependencies**:
{{outdated_dependencies_table}}

---

## Call Graph Analysis

### Critical Execution Paths

{{critical_paths_description}}

**Path Diagrams**:
```mermaid
graph TD
{{call_paths_mermaid}}
```

### Deep Call Stacks ({{deep_stacks_count}})

{{deep_call_stacks_table}}

**Call Depth Analysis**:
{{call_depth_analysis}}

---

## State Management Architecture

{{state_management_description}}

**State Layers**:
{{state_layers_diagram}}

**State Flow**:
```mermaid
flowchart LR
{{state_flow_mermaid}}
```

**State Management Issues**:
{{state_management_issues}}

---

## Data Flow Architecture

{{data_flow_description}}

**Data Flow Diagram**:
```mermaid
graph LR
{{data_flow_mermaid}}
```

**Data Transformation Points**:
{{data_transformation_points}}

---

## Testing Architecture

**Test Structure**:
{{test_structure_description}}

**Coverage by Layer**:
{{coverage_by_layer_table}}

**Testing Gaps**:
{{testing_gaps}}

---

## Performance Architecture

{{performance_architecture_description}}

**Performance Bottlenecks Identified**:
{{performance_bottlenecks_table}}

**Optimization Opportunities**:
{{optimization_opportunities}}

---

## Security Architecture

{{security_architecture_description}}

**Security Layers**:
{{security_layers_table}}

**Security Issues**:
{{security_issues_table}}

**Recommendations**:
{{security_recommendations}}

---

## Scalability Assessment

{{scalability_assessment}}

**Scaling Concerns**:
{{scaling_concerns_table}}

**Recommendations**:
{{scalability_recommendations}}

---

## Anti-Patterns Detected

{{anti_patterns_table}}

**Anti-Pattern Analysis**:
{{anti_pattern_analysis}}

---

## Architecture Recommendations

### Critical (Fix Immediately)

{{critical_recommendations}}

### High Priority (Fix Within Sprint)

{{high_priority_recommendations}}

### Medium Priority (Plan for Next Quarter)

{{medium_priority_recommendations}}

### Low Priority (Technical Debt)

{{low_priority_recommendations}}

---

## Refactoring Roadmap

### Phase 1: Immediate Fixes ({{phase1_duration}})

{{phase1_tasks}}

### Phase 2: Structural Improvements ({{phase2_duration}})

{{phase2_tasks}}

### Phase 3: Architecture Evolution ({{phase3_duration}})

{{phase3_tasks}}

**Estimated Effort**:
{{refactoring_effort_estimate}}

---

## Compliance Checklist

### Best Practices

{{best_practices_checklist}}

### Framework Guidelines

{{framework_guidelines_checklist}}

### Internal Standards

{{internal_standards_checklist}}

---

## Evidence Chain (CoD^Σ)

### Intelligence Queries Executed

```
{{intelligence_queries_cod}}
```

**Analysis Process**:
```
Step 1: ImportGraphMapping → {{import_edges_count}} edges analyzed
Step 2: TraceCallPaths → {{call_paths_count}} paths traced
Step 3: CircularDependencyDetection → {{cycles_count}} cycles found
Step 4: MetricsCalculation → {{metrics_calculated_count}} metrics computed
Step 5: PatternIdentification → {{patterns_identified_count}} patterns detected
```

**Total Token Usage**:
- Intel Queries: {{intel_tokens}} tokens
- Targeted Reads: {{read_tokens}} tokens
- MCP Verification: {{mcp_tokens}} tokens
- Analysis: {{analysis_tokens}} tokens
- Output: {{output_tokens}} tokens
- **Total**: {{total_tokens}} tokens

**vs. Reading Full System**: {{baseline_tokens}} tokens
**Savings**: {{savings_percentage}}%

---

## Appendix A: Complete Import Graph

{{complete_import_graph}}

---

## Appendix B: Metrics by File

{{metrics_by_file_table}}

---

## Appendix C: Pattern Usage Matrix

{{pattern_usage_matrix}}

---

**Reference**: This architecture analysis should be referenced in `CLAUDE.md` as:

```markdown
## Reference Inventory

- **@report.md** - Architecture analysis (generated {{timestamp}})
```

**Regenerate When**:
- Major refactoring completed
- New architectural layers added
- Significant dependency changes
- Every 60 days for active projects

---

**Generated by**: analyze-code skill (architecture mode)
**Workflow**: @.claude/skills/analyze-code/workflows/architecture-workflow.md
**Intelligence Tool**: @.claude/shared-imports/project-intel-mjs-guide.md
