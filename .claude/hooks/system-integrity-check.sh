#!/usr/bin/env bash
# System Integrity Check for Intelligence Toolkit
# Validates components, workflows, best practices, and constitutional compliance

set -e

# Set project directory (default to current directory if not set)
if [ -z "$CLAUDE_PROJECT_DIR" ]; then
  CLAUDE_PROJECT_DIR="$(pwd)"
fi

# Parse arguments
VERBOSE=false
FIX=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose) VERBOSE=true; shift ;;
    --fix) FIX=true; shift ;;
    *) shift ;;
  esac
done

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# Helper functions
pass() {
  echo -e "${GREEN}✓${NC} $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

warn() {
  echo -e "${YELLOW}⚠️${NC}  $1"
  WARN_COUNT=$((WARN_COUNT + 1))
}

fail() {
  echo -e "${RED}❌${NC} $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

section() {
  echo ""
  echo "=== $1 ==="
  echo ""
}

# Main validation
echo "=== Intelligence Toolkit System Integrity Check ==="
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

################################################################################
# 1. COMPONENT INVENTORY
################################################################################

section "1. Component Inventory"

# Count components
SKILL_COUNT=$(find "$CLAUDE_PROJECT_DIR/.claude/skills" -name "SKILL.md" -type f 2>/dev/null | wc -l | tr -d ' ')
CMD_COUNT=$(ls -1 "$CLAUDE_PROJECT_DIR/.claude/commands"/*.md 2>/dev/null | wc -l | tr -d ' ')
AGENT_COUNT=$(ls -1 "$CLAUDE_PROJECT_DIR/.claude/agents"/*.md 2>/dev/null | wc -l | tr -d ' ')
TEMPLATE_COUNT=$(ls -1 "$CLAUDE_PROJECT_DIR/.claude/templates"/*.md 2>/dev/null | wc -l | tr -d ' ')

echo "Skills: $SKILL_COUNT"
echo "Commands: $CMD_COUNT"
echo "Agents: $AGENT_COUNT"
echo "Templates: $TEMPLATE_COUNT"

if [ "$SKILL_COUNT" -ge 10 ]; then
  pass "Skill count: $SKILL_COUNT (expected ≥10)"
else
  warn "Skill count: $SKILL_COUNT (expected ≥10)"
fi

if [ "$CMD_COUNT" -ge 7 ]; then
  pass "Command count: $CMD_COUNT (expected ≥7)"
else
  warn "Command count: $CMD_COUNT (expected ≥7)"
fi

if [ "$AGENT_COUNT" -eq 4 ]; then
  pass "Agent count: $AGENT_COUNT (expected 4)"
else
  warn "Agent count: $AGENT_COUNT (expected 4)"
fi

# Check YAML frontmatter in skills
echo ""
echo "Checking skill YAML frontmatter..."
SKILL_YAML_ERRORS=0
for skill in "$CLAUDE_PROJECT_DIR/.claude/skills"/*/SKILL.md; do
  skillname=$(echo "$skill" | sed "s|$CLAUDE_PROJECT_DIR/.claude/skills/||; s|/SKILL.md||")

  # Check for name field
  if ! grep -q "^name:" "$skill" 2>/dev/null; then
    fail "  $skillname: Missing 'name' field"
    SKILL_YAML_ERRORS=$((SKILL_YAML_ERRORS + 1))
  fi

  # Check for description field
  if ! grep -q "^description:" "$skill" 2>/dev/null; then
    fail "  $skillname: Missing 'description' field"
    SKILL_YAML_ERRORS=$((SKILL_YAML_ERRORS + 1))
  fi
done

if [ "$SKILL_YAML_ERRORS" -eq 0 ]; then
  pass "All skills have valid YAML frontmatter"
else
  fail "YAML errors in $SKILL_YAML_ERRORS skill(s)"
fi

# Check YAML frontmatter in commands
echo ""
echo "Checking command YAML frontmatter..."
CMD_YAML_ERRORS=0
for cmd in "$CLAUDE_PROJECT_DIR/.claude/commands"/*.md; do
  cmdname=$(basename "$cmd" .md)

  # Check for description field
  if ! grep -q "^description:" "$cmd" 2>/dev/null; then
    fail "  $cmdname: Missing 'description' field (required for SlashCommand tool)"
    CMD_YAML_ERRORS=$((CMD_YAML_ERRORS + 1))
  fi
done

if [ "$CMD_YAML_ERRORS" -eq 0 ]; then
  pass "All commands have valid YAML frontmatter"
else
  fail "YAML errors in $CMD_YAML_ERRORS command(s)"
fi

# Check YAML frontmatter in agents
echo ""
echo "Checking agent YAML frontmatter..."
AGENT_YAML_ERRORS=0
for agent in "$CLAUDE_PROJECT_DIR/.claude/agents"/*.md; do
  agentname=$(basename "$agent" .md)

  # Check for name field
  if ! grep -q "^name:" "$agent" 2>/dev/null; then
    fail "  $agentname: Missing 'name' field"
    AGENT_YAML_ERRORS=$((AGENT_YAML_ERRORS + 1))
  fi

  # Check for description field
  if ! grep -q "^description:" "$agent" 2>/dev/null; then
    fail "  $agentname: Missing 'description' field"
    AGENT_YAML_ERRORS=$((AGENT_YAML_ERRORS + 1))
  fi

  # Check for model field
  if ! grep -q "^model:" "$agent" 2>/dev/null; then
    warn "  $agentname: Missing 'model' field (consider 'inherit' or specific model)"
  fi
done

if [ "$AGENT_YAML_ERRORS" -eq 0 ]; then
  pass "All agents have valid YAML frontmatter"
else
  fail "YAML errors in $AGENT_YAML_ERRORS agent(s)"
fi

################################################################################
# 2. WORKFLOW CHAIN INTEGRITY
################################################################################

section "2. Workflow Chain Integrity"

# Check SDD workflow chain
echo "Checking SDD workflow chain..."

# specify-feature should reference /plan
if grep -q "/plan" "$CLAUDE_PROJECT_DIR/.claude/skills/specify-feature/SKILL.md" 2>/dev/null; then
  pass "specify-feature → /plan connection: OK"
else
  fail "specify-feature → /plan connection: MISSING"
fi

# generate-tasks should reference /audit
if grep -q "/audit" "$CLAUDE_PROJECT_DIR/.claude/skills/generate-tasks/SKILL.md" 2>/dev/null; then
  pass "generate-tasks → /audit connection: OK"
else
  fail "generate-tasks → /audit connection: MISSING"
fi

# implement-and-verify should reference /verify
if grep -q "/verify" "$CLAUDE_PROJECT_DIR/.claude/skills/implement-and-verify/SKILL.md" 2>/dev/null; then
  pass "implement-and-verify → /verify connection: OK"
else
  fail "implement-and-verify → /verify connection: MISSING"
fi

# Check SlashCommand tool references
echo ""
echo "Checking SlashCommand tool references..."
SLASHCMD_REFS=$(grep -r "SlashCommand" "$CLAUDE_PROJECT_DIR/.claude/skills"/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$SLASHCMD_REFS" -gt 0 ]; then
  pass "SlashCommand tool referenced in skills: $SLASHCMD_REFS mentions"
else
  warn "SlashCommand tool not referenced in any skills"
fi

# Check Task tool usage in orchestrator
if grep -q "Task(" "$CLAUDE_PROJECT_DIR/.claude/agents/workflow-orchestrator.md" 2>/dev/null; then
  TASK_EXAMPLES=$(grep -c "Task(" "$CLAUDE_PROJECT_DIR/.claude/agents/workflow-orchestrator.md" 2>/dev/null || echo "0")
  pass "Orchestrator has Task tool examples: $TASK_EXAMPLES"
else
  fail "Orchestrator missing Task tool examples"
fi

################################################################################
# 3. BEST PRACTICES COMPLIANCE
################################################################################

section "3. Best Practices Compliance"

# Check skill line counts (<500 recommended)
echo "Checking skill line counts (recommended <500 lines)..."
OVERSIZED_SKILLS=0
for skill in "$CLAUDE_PROJECT_DIR/.claude/skills"/*/SKILL.md; do
  skillname=$(echo "$skill" | sed "s|$CLAUDE_PROJECT_DIR/.claude/skills/||; s|/SKILL.md||")
  lines=$(wc -l < "$skill" | tr -d ' ')

  if [ "$lines" -gt 500 ]; then
    warn "  $skillname: $lines lines (exceeds 500 recommended)"
    OVERSIZED_SKILLS=$((OVERSIZED_SKILLS + 1))
  elif [ "$VERBOSE" = true ]; then
    echo "  $skillname: $lines lines ✓"
  fi
done

if [ "$OVERSIZED_SKILLS" -eq 0 ]; then
  pass "All skills within 500-line limit"
else
  warn "$OVERSIZED_SKILLS skill(s) exceed 500-line recommendation"
fi

# Check hook JSON output format
echo ""
echo "Checking hook JSON output format..."
HOOKS_WITH_JSON=0
for hook in "$CLAUDE_PROJECT_DIR/.claude/hooks"/*.sh; do
  if [ -f "$hook" ]; then
    hookname=$(basename "$hook")
    if grep -q "\"decision\"\|\"hookSpecificOutput\"" "$hook" 2>/dev/null; then
      HOOKS_WITH_JSON=$((HOOKS_WITH_JSON + 1))
      if [ "$VERBOSE" = true ]; then
        echo "  $hookname: Uses JSON output ✓"
      fi
    else
      warn "  $hookname: Not using JSON output format"
    fi
  fi
done

if [ "$HOOKS_WITH_JSON" -gt 0 ]; then
  pass "$HOOKS_WITH_JSON hook(s) use JSON output format"
else
  warn "No hooks use JSON output format (recommend structured output)"
fi

# Check template CoD^Σ usage
echo ""
echo "Checking template CoD^Σ usage..."
TEMPLATES_WITHOUT_COD=0
for template in "$CLAUDE_PROJECT_DIR/.claude/templates"/*.md; do
  if [ -f "$template" ]; then
    # Skip bootstrap and documentation templates
    templatename=$(basename "$template")
    if [[ "$templatename" =~ (BOOTSTRAP|README|template\.md)$ ]]; then
      continue
    fi

    if ! grep -q "CoD" "$template" 2>/dev/null; then
      warn "  $templatename: No CoD^Σ notation found"
      TEMPLATES_WITHOUT_COD=$((TEMPLATES_WITHOUT_COD + 1))
    elif [ "$VERBOSE" = true ]; then
      echo "  $templatename: Has CoD^Σ ✓"
    fi
  fi
done

if [ "$TEMPLATES_WITHOUT_COD" -eq 0 ]; then
  pass "All workflow templates use CoD^Σ notation"
else
  warn "$TEMPLATES_WITHOUT_COD workflow template(s) missing CoD^Σ notation"
fi

# Check hooks are executable
echo ""
echo "Checking hook executability..."
NON_EXECUTABLE_HOOKS=0
for hook in "$CLAUDE_PROJECT_DIR/.claude/hooks"/*.sh; do
  if [ -f "$hook" ]; then
    hookname=$(basename "$hook")
    if [ ! -x "$hook" ]; then
      fail "  $hookname: Not executable (chmod +x needed)"
      NON_EXECUTABLE_HOOKS=$((NON_EXECUTABLE_HOOKS + 1))
    elif [ "$VERBOSE" = true ]; then
      echo "  $hookname: Executable ✓"
    fi
  fi
done

if [ "$NON_EXECUTABLE_HOOKS" -eq 0 ]; then
  pass "All hooks are executable"
else
  fail "$NON_EXECUTABLE_HOOKS hook(s) not executable"
fi

################################################################################
# 4. CONSTITUTIONAL COMPLIANCE
################################################################################

section "4. Constitutional Compliance"

# Check agents import constitution.md
echo "Checking agents import constitution.md..."
AGENTS_WITHOUT_CONSTITUTION=0
for agent in "$CLAUDE_PROJECT_DIR/.claude/agents"/*.md; do
  agentname=$(basename "$agent" .md)
  if ! grep -q "@.claude/shared-imports/constitution.md" "$agent" 2>/dev/null; then
    fail "  $agentname: Missing constitution.md import"
    AGENTS_WITHOUT_CONSTITUTION=$((AGENTS_WITHOUT_CONSTITUTION + 1))
  elif [ "$VERBOSE" = true ]; then
    echo "  $agentname: Imports constitution.md ✓"
  fi
done

if [ "$AGENTS_WITHOUT_CONSTITUTION" -eq 0 ]; then
  pass "All agents import constitution.md"
else
  fail "$AGENTS_WITHOUT_CONSTITUTION agent(s) missing constitution.md import"
fi

# Check skills reference constitutional articles
echo ""
echo "Checking skills reference constitutional articles..."
SKILLS_WITH_ARTICLES=$(grep -l "Article" "$CLAUDE_PROJECT_DIR/.claude/skills"/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$SKILLS_WITH_ARTICLES" -gt 5 ]; then
  pass "$SKILLS_WITH_ARTICLES skills reference constitutional articles"
else
  warn "Only $SKILLS_WITH_ARTICLES skills reference constitutional articles"
fi

# Check quality-checklist.md exists
if [ -f "$CLAUDE_PROJECT_DIR/.claude/templates/quality-checklist.md" ]; then
  pass "Quality checklist template exists"
else
  warn "Quality checklist template missing"
fi

# Check intelligence-first pattern (project-intel.mjs references)
INTEL_REFERENCES=$(grep -r "project-intel.mjs" "$CLAUDE_PROJECT_DIR/.claude/skills" "$CLAUDE_PROJECT_DIR/.claude/agents" 2>/dev/null | wc -l | tr -d ' ')
if [ "$INTEL_REFERENCES" -gt 5 ]; then
  pass "Intelligence-first approach: $INTEL_REFERENCES references to project-intel.mjs"
else
  warn "Low intelligence-first adoption: only $INTEL_REFERENCES references to project-intel.mjs"
fi

################################################################################
# 5. SUMMARY
################################################################################

section "Summary"

echo "✓ PASS:    $PASS_COUNT checks"
echo "⚠️  WARNING: $WARN_COUNT issues"
echo "❌ FAIL:    $FAIL_COUNT critical issues"
echo ""

# Overall status
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "Overall Status: ❌ CRITICAL FAILURES - System integrity compromised"
  echo "Action Required: Fix failures before production use"
  exit 1
elif [ "$WARN_COUNT" -gt 0 ]; then
  echo "Overall Status: ⚠️  WARNINGS - Review recommended"
  echo "Action Suggested: Address high-impact warnings"
  exit 0
else
  echo "Overall Status: ✓ ALL CHECKS PASSED - System healthy"
  exit 0
fi
