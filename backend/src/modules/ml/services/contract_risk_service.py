"""``ContractRiskService`` -- Phase 9. Smart contract security risk scoring.

Integration point: Phase 4's ``IssuanceService.launch()`` can optionally call
``score_contract_risk()`` before ``LAUNCHED`` status if contract deployment
is involved.

Current implementation uses simple heuristic scoring (presence of risky
patterns like selfdestruct, unchecked calls, etc.). Production deployment
should integrate Slither/Mythril for comprehensive static analysis.
"""

from __future__ import annotations

from typing import Any

from austial.common import Injectable
from austial.orm import InjectRepository, Repository

from src.modules.ml.entities.ml_prediction import MlPrediction


@Injectable()
class ContractRiskService:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
    ):
        self.ml_prediction_repo = ml_prediction_repo

    async def score_contract_risk(
        self,
        bytecode: str | None,
        source_code: str | None,
        contract_id: int | None = None,
    ) -> dict[str, Any]:
        """Score smart contract security risk.

        Args:
            bytecode: Contract bytecode (hex string)
            source_code: Contract source code (Solidity)
            contract_id: SmartContractDeployment ID for audit logging

        Returns:
            Dict with risk_score (0-100), risk_level, findings list
        """
        try:
            findings = []
            risk_score = 0.0

            if source_code:
                source_findings = self._analyze_source_code(source_code)
                findings.extend(source_findings)
                risk_score += sum(f["severity_points"] for f in source_findings)

            if bytecode:
                bytecode_findings = self._analyze_bytecode(bytecode)
                findings.extend(bytecode_findings)
                risk_score += sum(f["severity_points"] for f in bytecode_findings)

            risk_score = min(risk_score, 100)
            risk_level = self._categorize_risk(risk_score)

            result = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "findings": findings,
                "findings_count": len(findings),
            }

            await self._log_prediction(
                model_name="contract_risk",
                model_version="heuristic_v1.0",
                input_features={
                    "has_bytecode": bytecode is not None,
                    "has_source": source_code is not None,
                    "bytecode_length": len(bytecode) if bytecode else 0,
                    "source_length": len(source_code) if source_code else 0,
                },
                prediction_output=result,
                confidence_score=risk_score / 100.0,
                entity_type="SmartContractDeployment",
                entity_id=contract_id,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="contract_risk",
                model_version="heuristic_v1.0",
                input_features={
                    "has_bytecode": bytecode is not None,
                    "has_source": source_code is not None,
                },
                prediction_output={"error": str(e)},
                confidence_score=0.0,
                entity_type="SmartContractDeployment",
                entity_id=contract_id,
            )
            raise

    def _analyze_source_code(self, source_code: str) -> list[dict[str, Any]]:
        """Heuristic analysis of Solidity source code."""
        findings = []

        if "selfdestruct" in source_code.lower():
            findings.append(
                {
                    "type": "selfdestruct_present",
                    "severity": "HIGH",
                    "severity_points": 30,
                    "description": "Contract contains selfdestruct which can destroy the contract",
                }
            )

        if ".call(" in source_code and "require(" not in source_code:
            findings.append(
                {
                    "type": "unchecked_external_call",
                    "severity": "HIGH",
                    "severity_points": 25,
                    "description": "External call without proper error handling",
                }
            )

        if "tx.origin" in source_code:
            findings.append(
                {
                    "type": "tx_origin_usage",
                    "severity": "MEDIUM",
                    "severity_points": 15,
                    "description": "Usage of tx.origin for authorization (phishing risk)",
                }
            )

        if "delegatecall" in source_code.lower():
            findings.append(
                {
                    "type": "delegatecall_usage",
                    "severity": "MEDIUM",
                    "severity_points": 20,
                    "description": "Delegatecall usage requires careful context preservation",
                }
            )

        if source_code.count("public") > source_code.count("private") * 2:
            findings.append(
                {
                    "type": "excessive_public_functions",
                    "severity": "LOW",
                    "severity_points": 10,
                    "description": "Many public functions increase attack surface",
                }
            )

        return findings

    def _analyze_bytecode(self, bytecode: str) -> list[dict[str, Any]]:
        """Heuristic analysis of contract bytecode."""
        findings = []

        if len(bytecode) > 50000:
            findings.append(
                {
                    "type": "large_bytecode",
                    "severity": "LOW",
                    "severity_points": 5,
                    "description": "Large bytecode size may indicate complexity",
                }
            )

        suspicious_opcodes = ["ff", "f4", "f2"]
        for opcode in suspicious_opcodes:
            if opcode in bytecode.lower():
                findings.append(
                    {
                        "type": f"suspicious_opcode_{opcode}",
                        "severity": "MEDIUM",
                        "severity_points": 15,
                        "description": f"Suspicious opcode {opcode} detected",
                    }
                )

        return findings

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into levels."""
        if risk_score >= 70:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 30:
            return "MEDIUM"
        else:
            return "LOW"

    async def _log_prediction(
        self,
        model_name: str,
        model_version: str,
        input_features: dict[str, Any],
        prediction_output: dict[str, Any],
        confidence_score: float | None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        """Internal helper: log every prediction to MlPrediction table."""
        prediction = MlPrediction()
        prediction.model_name = model_name
        prediction.model_version = model_version
        prediction.input_features = input_features
        prediction.prediction_output = prediction_output
        prediction.confidence_score = confidence_score
        prediction.entity_type = entity_type
        prediction.entity_id = entity_id

        await self.ml_prediction_repo.save(prediction)
