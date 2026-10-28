"""
会诊会话持久化与用户数据空间

设计：
- 每个用户有独立的数据空间：data/userdata/<user_id>/
- 会诊申请与报告持久化到：data/userdata/<user_id>/consultations/
- 审计日志持久化到：data/audit/audit.log（管理员可见）
- 管理员可查看全局会诊记录（跨用户）
"""
import json
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, date

from .patient import Patient, MedicalImage
from .moderator import ConsultationReport


def get_project_root() -> Path:
    """获取项目根目录，兼容开发环境和 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，使用 sys._MEIPASS 获取资源目录
        return Path(sys._MEIPASS)
    else:
        # 开发环境：从当前文件位置推算项目根目录
        return Path(__file__).parent.parent.parent


class AuditLogger:
    """审计日志 - 记录所有敏感操作"""

    def __init__(self, audit_dir: str = None):
        if audit_dir is None:
            project_root = get_project_root()
            audit_dir = project_root / "data" / "audit"
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.audit_dir / "audit.log"

    def log(self, user_id: str, username: str, action: str,
            target: str = "", detail: str = "", ip: str = "") -> None:
        """记录一条审计日志

        :param user_id: 操作者 ID
        :param username: 操作者用户名
        :param action: 动作（LOGIN/LOGOUT/CREATE_CONSULTATION/APPROVE_REPORT 等）
        :param target: 操作目标（如会诊 ID）
        :param detail: 详细信息
        :param ip: 来源 IP
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "username": username,
            "action": action,
            "target": target,
            "detail": detail,
            "ip": ip,
        }
        # 追加写入，每行一条 JSON
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_logs(self, limit: int = 500, action: str = None,
                 user_id: str = None) -> List[Dict[str, Any]]:
        """读取审计日志

        :param limit: 最多返回条数（最新 N 条）
        :param action: 按动作过滤（可选）
        :param user_id: 按用户过滤（可选）
        """
        if not self.log_file.exists():
            return []
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if action and entry.get("action") != action:
                        continue
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        # 返回最新 limit 条
        return entries[-limit:][::-1]


class UserSession:
    """用户会话 - 持久化每个用户的会诊数据"""

    def __init__(self, user_id: str, data_root: str = None):
        self.user_id = user_id
        if data_root is None:
            project_root = get_project_root()
            data_root = project_root / "data" / "userdata"
        self.data_root = Path(data_root)
        self.user_dir = self.data_root / user_id
        self.consultations_dir = self.user_dir / "consultations"
        self.patients_dir = self.user_dir / "patients"
        self.images_dir = self.user_dir / "images"
        self.consultations_dir.mkdir(parents=True, exist_ok=True)
        self.patients_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: ConsultationReport) -> Path:
        """持久化会诊报告"""
        filepath = self.consultations_dir / f"{report.consultation_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return filepath

    def load_report(self, consultation_id: str) -> Optional[ConsultationReport]:
        """加载会诊报告"""
        filepath = self.consultations_dir / f"{consultation_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 用 from_dict 重建（需要扩展 ConsultationReport 支持 from_dict）
            return _report_from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def list_reports(self) -> List[Dict[str, Any]]:
        """列出该用户的所有会诊报告摘要"""
        results = []
        if not self.consultations_dir.exists():
            return results
        for f in sorted(self.consultations_dir.glob("*.json"), reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({
                    "consultation_id": data.get("consultation_id", ""),
                    "patient_id": data.get("patient_id", ""),
                    "patient_name": data.get("patient_name", ""),
                    "consultation_type": data.get("consultation_type", ""),
                    "status": data.get("status", ""),
                    "created_at": data.get("created_at", ""),
                    "completed_at": data.get("completed_at", ""),
                    "filename": f.name,
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def delete_report(self, consultation_id: str) -> bool:
        filepath = self.consultations_dir / f"{consultation_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def save_patient(self, patient: Patient) -> Path:
        """保存患者到用户空间"""
        filepath = self.patients_dir / f"{patient.patient_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(patient.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return filepath

    def load_patient(self, patient_id: str) -> Optional[Patient]:
        filepath = self.patients_dir / f"{patient_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Patient.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def list_patients(self) -> List[Dict[str, Any]]:
        """列出该用户空间的所有患者摘要"""
        results = []
        if not self.patients_dir.exists():
            return results
        for f in sorted(self.patients_dir.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({
                    "patient_id": data.get("patient_id", ""),
                    "name": data.get("name", ""),
                    "gender": data.get("gender", ""),
                    "age": data.get("age", 0),
                    "department": data.get("department", ""),
                    "filename": f.name,
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def delete_patient(self, patient_id: str) -> bool:
        filepath = self.patients_dir / f"{patient_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def save_medical_image(self, patient_id: str, source_path: str,
                           image_type: str = "其他", body_part: str = "",
                           description: str = "") -> MedicalImage:
        """保存医学影像图片到用户空间

        :param patient_id: 关联患者ID
        :param source_path: 原始图片路径
        :param image_type: 影像类型
        :param body_part: 部位
        :param description: 描述
        :return: MedicalImage 元数据对象
        """
        source = Path(source_path)
        if not source.exists():
            raise ValueError(f"源文件不存在: {source_path}")

        image_id = f"IMG-{uuid.uuid4().hex[:12].upper()}"
        ext = source.suffix.lower() if source.suffix else ".jpg"
        dest_name = f"{image_id}{ext}"
        dest_path = self.images_dir / dest_name
        shutil.copy2(source, dest_path)

        return MedicalImage(
            image_id=image_id,
            patient_id=patient_id,
            file_name=source.name,
            file_path=str(dest_path),
            image_type=image_type,
            body_part=body_part,
            description=description,
            uploaded_at=date.today(),
            file_size=dest_path.stat().st_size,
        )

    def load_medical_image(self, image_id: str) -> Optional[Path]:
        """根据图片ID查找本地文件路径"""
        for f in self.images_dir.iterdir():
            if f.stem == image_id and f.is_file():
                return f
        return None

    def list_medical_images(self, patient_id: str = None) -> List[Dict[str, Any]]:
        """列出医学影像图片元数据

        优先读取同目录下的 <image_id>.json 元数据文件；不存在时返回文件名等基本信息。
        """
        results = []
        if not self.images_dir.exists():
            return results
        for f in sorted(self.images_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() == ".json":
                continue
            meta_file = f.with_suffix(".json")
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if patient_id and data.get("patient_id") != patient_id:
                        continue
                    results.append(data)
                    continue
                except (json.JSONDecodeError, OSError):
                    pass
            # 无元数据文件时兜底
            if patient_id:
                continue
            results.append({
                "image_id": f.stem,
                "patient_id": "",
                "file_name": f.name,
                "file_path": str(f),
                "image_type": "未知",
                "file_size": f.stat().st_size,
            })
        return results

    def save_medical_image_meta(self, image: MedicalImage) -> Path:
        """保存 MedicalImage 元数据到 JSON 文件"""
        meta_path = self.images_dir / f"{image.image_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(image.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return meta_path

    def delete_medical_image(self, image_id: str) -> bool:
        """删除医学影像图片及其元数据"""
        deleted = False
        for f in self.images_dir.iterdir():
            if f.stem == image_id:
                f.unlink(missing_ok=True)
                deleted = True
        return deleted


class GlobalConsultationIndex:
    """全局会诊索引 - 供管理员查看所有用户的会诊记录"""

    def __init__(self, data_root: str = None):
        if data_root is None:
            project_root = Path(__file__).parent.parent.parent
            data_root = project_root / "data" / "userdata"
        self.data_root = Path(data_root)

    def list_all_reports(self) -> List[Dict[str, Any]]:
        """列出所有用户的所有会诊报告"""
        results = []
        if not self.data_root.exists():
            return results
        for user_dir in self.data_root.iterdir():
            if not user_dir.is_dir():
                continue
            user_id = user_dir.name
            consultations_dir = user_dir / "consultations"
            if not consultations_dir.exists():
                continue
            for f in sorted(consultations_dir.glob("*.json"), reverse=True):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    results.append({
                        "user_id": user_id,
                        "consultation_id": data.get("consultation_id", ""),
                        "patient_id": data.get("patient_id", ""),
                        "patient_name": data.get("patient_name", ""),
                        "consultation_type": data.get("consultation_type", ""),
                        "status": data.get("status", ""),
                        "created_at": data.get("created_at", ""),
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        # 按时间倒序
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    def load_report(self, user_id: str, consultation_id: str):
        """跨用户加载会诊报告（供审核员查看医生提交的报告）

        :param user_id: 报告所属用户（医生）的 ID
        :param consultation_id: 会诊编号
        :return: ConsultationReport 对象或 None
        """
        filepath = self.data_root / user_id / "consultations" / f"{consultation_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _report_from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def update_report_status(self, user_id: str, consultation_id: str,
                             new_status: str, extra_fields: dict = None) -> bool:
        """跨用户更新报告状态（审核员审核后回写医生空间的报告文件）

        :param user_id: 报告所属用户（医生）的 ID
        :param consultation_id: 会诊编号
        :param new_status: 新状态（如 APPROVED / REJECTED）
        :param extra_fields: 额外字段（如 reviewer, reviewed_at）
        :return: 是否更新成功
        """
        filepath = self.data_root / user_id / "consultations" / f"{consultation_id}.json"
        if not filepath.exists():
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = new_status
            if extra_fields:
                data.update(extra_fields)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except (json.JSONDecodeError, OSError, KeyError):
            return False


class ReviewQueue:
    """审核队列 - 管理医生提交的待审核报告，实现「医生提交→审核员审核」闭环

    数据持久化到 data/review_queue/queue.json（原子写入）
    每条记录包含：
      - submission_id: 提交记录 ID
      - consultation_id: 会诊编号
      - doctor_id / doctor_name: 提交医生信息
      - patient_id / patient_name: 患者信息
      - consultation_type / priority: 会诊类型与优先级
      - department: 科室
      - submitted_at: 提交时间
      - status: PENDING / APPROVED / REJECTED
      - reviewer_id / reviewer_name: 审核员信息（审核后填入）
      - reviewed_at: 审核时间
      - review_comment: 审核意见
    """

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    def __init__(self, data_root: str = None):
        if data_root is None:
            project_root = get_project_root()
            data_root = project_root / "data" / "review_queue"
        self.data_dir = Path(data_root)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.data_dir / "queue.json"

    def _load(self) -> List[Dict[str, Any]]:
        """加载审核队列数据"""
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, entries: List[Dict[str, Any]]) -> None:
        """原子写入审核队列数据"""
        tmp_file = self.queue_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2, default=str)
        tmp_file.replace(self.queue_file)

    def submit(self, consultation_id: str, doctor_id: str, doctor_name: str,
               patient_id: str = "", patient_name: str = "",
               consultation_type: str = "", priority: str = "常规",
               department: str = "", assigned_reviewer_id: str = "",
               assigned_reviewer_name: str = "") -> bool:
        """医生提交报告到审核队列

        :param assigned_reviewer_id: 指定审核员 ID（可空，为空表示任意审核员可审核）
        :param assigned_reviewer_name: 指定审核员姓名
        """
        entries = self._load()
        # 防止重复提交
        for e in entries:
            if e.get("consultation_id") == consultation_id:
                # 已提交过，更新状态为 PENDING（允许重新提交被驳回的）
                if e.get("status") == self.STATUS_REJECTED:
                    e["status"] = self.STATUS_PENDING
                    e["submitted_at"] = datetime.now().isoformat()
                    e["assigned_reviewer_id"] = assigned_reviewer_id
                    e["assigned_reviewer_name"] = assigned_reviewer_name
                    e.pop("reviewer_id", None)
                    e.pop("reviewer_name", None)
                    e.pop("reviewed_at", None)
                    e.pop("review_comment", None)
                    self._save(entries)
                    return True
                return False  # 已在队列中且非驳回状态
        entry = {
            "submission_id": f"RV-{uuid.uuid4().hex[:8].upper()}",
            "consultation_id": consultation_id,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "consultation_type": consultation_type,
            "priority": priority,
            "department": department,
            "assigned_reviewer_id": assigned_reviewer_id,
            "assigned_reviewer_name": assigned_reviewer_name,
            "submitted_at": datetime.now().isoformat(),
            "status": self.STATUS_PENDING,
        }
        entries.append(entry)
        self._save(entries)
        return True

    def withdraw(self, consultation_id: str) -> bool:
        """医生撤回尚未审核的提交"""
        entries = self._load()
        new_entries = []
        removed = False
        for e in entries:
            if e.get("consultation_id") == consultation_id:
                if e.get("status") == self.STATUS_PENDING:
                    removed = True
                    continue  # 跳过（删除）
            new_entries.append(e)
        if removed:
            self._save(new_entries)
        return removed

    def list_pending(self, reviewer_id: str = None) -> List[Dict[str, Any]]:
        """列出待审核报告（供审核员查看）

        :param reviewer_id: 当前审核员 ID。传入时仅显示指定给该审核员或未指定审核员的报告。
        """
        entries = self._load()
        pending = []
        for e in entries:
            if e.get("status") != self.STATUS_PENDING:
                continue
            if reviewer_id:
                assigned = e.get("assigned_reviewer_id", "")
                if assigned and assigned != reviewer_id:
                    continue
            pending.append(e)
        pending.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
        return pending

    def list_reviewed_by(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """列出某审核员的历史审核记录"""
        entries = self._load()
        reviewed = [e for e in entries
                     if e.get("reviewer_id") == reviewer_id
                     and e.get("status") in (self.STATUS_APPROVED, self.STATUS_REJECTED)]
        reviewed.sort(key=lambda x: x.get("reviewed_at", ""), reverse=True)
        return reviewed

    def list_all_reviewed(self) -> List[Dict[str, Any]]:
        """列出所有已审核记录"""
        entries = self._load()
        reviewed = [e for e in entries
                     if e.get("status") in (self.STATUS_APPROVED, self.STATUS_REJECTED)]
        reviewed.sort(key=lambda x: x.get("reviewed_at", ""), reverse=True)
        return reviewed

    def get_entry(self, consultation_id: str) -> Optional[Dict[str, Any]]:
        """获取某会诊报告的审核状态"""
        entries = self._load()
        for e in entries:
            if e.get("consultation_id") == consultation_id:
                return e
        return None

    def approve(self, consultation_id: str, reviewer_id: str,
                reviewer_name: str, comment: str = "") -> bool:
        """审核通过"""
        entries = self._load()
        for e in entries:
            if e.get("consultation_id") == consultation_id:
                if e.get("status") != self.STATUS_PENDING:
                    return False
                e["status"] = self.STATUS_APPROVED
                e["reviewer_id"] = reviewer_id
                e["reviewer_name"] = reviewer_name
                e["reviewed_at"] = datetime.now().isoformat()
                e["review_comment"] = comment
                self._save(entries)
                return True
        return False

    def reject(self, consultation_id: str, reviewer_id: str,
               reviewer_name: str, comment: str = "") -> bool:
        """驳回报告"""
        entries = self._load()
        for e in entries:
            if e.get("consultation_id") == consultation_id:
                if e.get("status") != self.STATUS_PENDING:
                    return False
                e["status"] = self.STATUS_REJECTED
                e["reviewer_id"] = reviewer_id
                e["reviewer_name"] = reviewer_name
                e["reviewed_at"] = datetime.now().isoformat()
                e["review_comment"] = comment
                self._save(entries)
                return True
        return False

    def stats(self) -> Dict[str, int]:
        """审核队列统计"""
        entries = self._load()
        pending = sum(1 for e in entries if e.get("status") == self.STATUS_PENDING)
        approved = sum(1 for e in entries if e.get("status") == self.STATUS_APPROVED)
        rejected = sum(1 for e in entries if e.get("status") == self.STATUS_REJECTED)
        return {"pending": pending, "approved": approved, "rejected": rejected, "total": len(entries)}


def _report_from_dict(data: dict) -> ConsultationReport:
    """从 dict 重建 ConsultationReport（避免循环依赖，定义在此处）"""
    from .moderator import ConsultationReport, DiscussionRound
    from .evidence import Recommendation

    report = ConsultationReport(
        consultation_id=data.get("consultation_id", ""),
        patient_id=data.get("patient_id", ""),
        patient_name=data.get("patient_name", ""),
        consultation_type=data.get("consultation_type", ""),
        status=data.get("status", ""),
        created_at=data.get("created_at", ""),
        completed_at=data.get("completed_at"),
        participating_agents=data.get("participating_agents", []),
        differential_diagnosis=data.get("differential_diagnosis", []),
        recommended_tests=[Recommendation.from_dict(r) for r in data.get("recommended_tests", []) if isinstance(r, dict)],
        treatment_plan=[Recommendation.from_dict(r) for r in data.get("treatment_plan", []) if isinstance(r, dict)],
        medication_suggestions=[Recommendation.from_dict(r) for r in data.get("medication_suggestions", []) if isinstance(r, dict)],
        risk_assessment=data.get("risk_assessment", ""),
        follow_up_plan=data.get("follow_up_plan", []),
        discussion_summary=[
            DiscussionRound(
                round_number=d.get("round_number", 0),
                topic=d.get("topic", ""),
                consensus_points=d.get("consensus_points", []),
                disagreement_points=d.get("disagreement_points", []),
            ) for d in data.get("discussion_summary", []) if isinstance(d, dict)
        ],
        disagreements=data.get("disagreements", []),
        uncertainties=data.get("uncertainties", []),
        final_conclusion=data.get("final_conclusion", ""),
    )
    return report
