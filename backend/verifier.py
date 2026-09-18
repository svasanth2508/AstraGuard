from __future__ import annotations

from typing import Any


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == '<':
        return value < threshold
    if operator == '<=':
        return value <= threshold
    if operator == '>':
        return value > threshold
    if operator == '>=':
        return value >= threshold
    if operator == '==':
        return value == threshold
    raise ValueError(f'Unsupported operator: {operator}')


def verify_recovery(metrics: dict[str, float], contract: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for condition in contract.get('success_conditions', []):
        metric = condition['metric']
        value = float(metrics.get(metric, 0.0))
        threshold = float(condition['threshold'])
        passed = _compare(value, condition['operator'], threshold)
        checks.append({
            'metric': metric,
            'label': condition['label'],
            'value': round(value, 1),
            'threshold': threshold,
            'operator': condition['operator'],
            'passed': passed,
        })

    passed_count = sum(1 for check in checks if check['passed'])
    return {
        'status': 'PASSED' if checks and passed_count == len(checks) else 'FAILED',
        'passed': checks and passed_count == len(checks),
        'passed_checks': passed_count,
        'total_checks': len(checks),
        'checks': checks,
    }
