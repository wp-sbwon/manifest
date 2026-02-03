"""
Parse agent output into structured data by agent type and stage.

Used by AgentCoordinator to extract plan, test results, decisions, etc.
from raw agent output for use in subsequent workflow stages.
"""
import json
import re
from typing import Dict, Any, Optional


def parse_agent_output(
    agent_type: str,
    stage: Optional[str],
    output: str,
    tool_execution_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse agent output to extract structured data.

    Attempts to extract structured information from agent output based on
    agent type and stage. This helps Worker Squad use agent results in
    subsequent stages.

    Args:
        agent_type: Type of agent that produced the output.
        stage: Stage in the workflow.
        output: Raw agent output text.
        tool_execution_summary: Optional summary from tool execution (more reliable for some fields).

    Returns:
        Dictionary with parsed/structured data. Structure varies by agent type.
    """
    parsed: Dict[str, Any] = {}

    if agent_type == "planner":
        _parse_planner(output, parsed)
    elif agent_type == "test" and stage == "tdd_test":
        _parse_tdd_test(output, parsed)
    elif agent_type == "test" and stage == "test":
        _parse_test_results(output, parsed, tool_execution_summary)
    elif agent_type == "coder":
        _parse_coder(output, parsed, tool_execution_summary)
    elif agent_type == "approver":
        _parse_approver(output, parsed)
    elif agent_type == "debug":
        _parse_debug(output, parsed, tool_execution_summary)

    return parsed


def _parse_planner(output: str, parsed: Dict[str, Any]) -> None:
    json_match = re.search(r'\{[^{}]*"plan"[^{}]*\}', output, re.DOTALL)
    if json_match:
        try:
            plan_data = json.loads(json_match.group(0))
            parsed["plan"] = plan_data
        except (json.JSONDecodeError, TypeError):
            pass

    task_pattern = r'(?:Task|Step)\s*\d+[:\-]\s*(.+?)(?:\n|$)'
    tasks = re.findall(task_pattern, output, re.IGNORECASE | re.MULTILINE)
    if tasks:
        parsed["tasks"] = [t.strip() for t in tasks]

    time_match = re.search(r'(?:estimate|time|duration)[:\s]+(\d+)\s*(?:hours?|hrs?)', output, re.IGNORECASE)
    if time_match:
        parsed["estimated_hours"] = int(time_match.group(1))


def _parse_tdd_test(output: str, parsed: Dict[str, Any]) -> None:
    code_block_pattern = r'```(?:python|py|test)?\n(.*?)```'
    code_blocks = re.findall(code_block_pattern, output, re.DOTALL)
    if code_blocks:
        test_skeleton = max(code_blocks, key=len)
        parsed["test_skeleton"] = test_skeleton
        parsed["code_blocks"] = code_blocks

    plan_patterns = [
        r'(?:test\s+plan|plan|test\s+strategy)[:\s]+(.+?)(?:\n\n|\Z)',
        r'##\s*(?:Test\s+)?Plan\s*\n(.+?)(?:\n##|\Z)',
        r'Plan:\s*\n(.+?)(?:\n\n|\Z)',
    ]
    for pattern in plan_patterns:
        plan_match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
        if plan_match:
            parsed["test_plan"] = plan_match.group(1).strip()
            break


def _parse_test_results(
    output: str, parsed: Dict[str, Any], tool_execution_summary: Optional[Dict[str, Any]]
) -> None:
    if tool_execution_summary:
        if "test_results" in tool_execution_summary:
            parsed["test_results"] = tool_execution_summary["test_results"]
        if "tests_passed" in tool_execution_summary:
            parsed["tests_passed"] = tool_execution_summary["tests_passed"]
        if "tests_failed" in tool_execution_summary:
            parsed["tests_failed"] = tool_execution_summary["tests_failed"]
        if "errors" in tool_execution_summary:
            parsed["errors"] = tool_execution_summary["errors"]

    if "tests_passed" not in parsed:
        passed_match = re.search(r'(?:passed|PASSED)[:\s]+(\d+)', output, re.IGNORECASE)
        if passed_match:
            parsed["tests_passed"] = int(passed_match.group(1))

    if "tests_failed" not in parsed:
        failed_match = re.search(r'(?:failed|FAILED)[:\s]+(\d+)', output, re.IGNORECASE)
        if failed_match:
            parsed["tests_failed"] = int(failed_match.group(1))

    if "errors" not in parsed or not parsed.get("errors"):
        error_pattern = r'(?:error|ERROR|failure|FAILURE)[:\s]+(.+?)(?:\n|$)'
        errors = re.findall(error_pattern, output, re.IGNORECASE | re.MULTILINE)
        if errors:
            parsed["errors"] = [e.strip() for e in errors]


def _parse_coder(
    output: str, parsed: Dict[str, Any], tool_execution_summary: Optional[Dict[str, Any]]
) -> None:
    if tool_execution_summary:
        parsed["files_modified"] = tool_execution_summary.get("modified_files", [])
        parsed["executed_commands"] = tool_execution_summary.get("executed_commands", [])
        parsed["read_files"] = tool_execution_summary.get("read_files", [])
        parsed["errors"] = tool_execution_summary.get("errors", [])
        parsed["total_tool_calls"] = tool_execution_summary.get("total_tool_calls", 0)
    else:
        file_pattern = r'(?:modified|changed|updated)\s+file[:\s]+(.+?)(?:\n|$)'
        files = re.findall(file_pattern, output, re.IGNORECASE | re.MULTILINE)
        if files:
            parsed["files_modified"] = [f.strip() for f in files]

    code_blocks = re.findall(r'```(?:python|py|javascript|js|typescript|ts)?\n(.*?)```', output, re.DOTALL)
    if code_blocks:
        parsed["code_blocks"] = code_blocks


def _parse_approver(output: str, parsed: Dict[str, Any]) -> None:
    decision_patterns = [
        r'(?:decision|result|verdict|status)[:\s]+(approved|rejected|pending|accept|deny)',
        r'(?:I\s+)?(?:approve|reject|accept|deny|pending)',
        r'\[(?:APPROVED|REJECTED|PENDING)\]',
    ]
    for pattern in decision_patterns:
        decision_match = re.search(pattern, output, re.IGNORECASE)
        if decision_match:
            decision = decision_match.group(1) if decision_match.lastindex else decision_match.group(0)
            decision_lower = decision.lower() if isinstance(decision, str) else ""
            if "approve" in decision_lower or "accept" in decision_lower:
                parsed["decision"] = "approved"
            elif "reject" in decision_lower or "deny" in decision_lower:
                parsed["decision"] = "rejected"
            else:
                parsed["decision"] = "pending"
            break

    feedback_patterns = [
        r'(?:feedback|comment|notes|remarks)[:\s]+(.+?)(?:\n\n|\Z)',
        r'##\s*Feedback\s*\n(.+?)(?:\n##|\Z)',
        r'Feedback:\s*\n(.+?)(?:\n\n|\Z)',
    ]
    for pattern in feedback_patterns:
        feedback_match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)
        if feedback_match:
            parsed["feedback"] = feedback_match.group(1).strip()
            break


def _parse_debug(
    output: str, parsed: Dict[str, Any], tool_execution_summary: Optional[Dict[str, Any]]
) -> None:
    if tool_execution_summary:
        if "issues_fixed" in tool_execution_summary:
            parsed["issues_fixed"] = tool_execution_summary["issues_fixed"]
        if "fixes_applied" in tool_execution_summary:
            parsed["fixes_applied"] = tool_execution_summary["fixes_applied"]
        if "errors" in tool_execution_summary:
            parsed["errors"] = tool_execution_summary["errors"]

    if "issues_fixed" not in parsed:
        issue_patterns = [
            r'(?:fixed|resolved|issue|bug)[:\s]+(.+?)(?:\n|$)',
            r'[-*]\s*(?:Fixed|Resolved)[:\s]+(.+?)(?:\n|$)',
        ]
        all_issues = []
        for pattern in issue_patterns:
            issues = re.findall(pattern, output, re.IGNORECASE | re.MULTILINE)
            for issue in issues:
                issue_clean = issue.strip()
                if issue_clean and issue_clean not in all_issues:
                    all_issues.append(issue_clean)
        if all_issues:
            parsed["issues_fixed"] = all_issues
