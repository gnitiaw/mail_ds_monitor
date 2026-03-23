"""大模型服务封装。"""

import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """大模型调用错误。"""


class LLMTimeoutError(LLMError):
    """大模型调用超时。"""


class LLMResponseError(LLMError):
    """大模型响应错误。"""


EXTRACTION_PROMPT = """你是一个邮件内容分析助手。请从以下邮件中提取结构化信息。

邮件主题：{subject}
发件人：{sender}
邮件正文：
{body}

请提取以下信息并以 JSON 格式返回：
1. summary: 邮件摘要（100字以内）
2. business_type: 业务类型（如：订单、投诉、通知、合同、其他）
3. priority: 优先级（high、medium、low）
4. risk_tags: 风险标签列表（如：紧急、敏感、法律风险等）
5. action_items: 待办事项列表
6. entities: 关键实体（如客户名、订单号、金额等）

返回格式：
{{
  "summary": "...",
  "business_type": "...",
  "priority": "...",
  "risk_tags": [...],
  "action_items": [...],
  "entities": {{...}}
}}

只返回 JSON，不要包含其他内容。"""


SUMMARY_PROMPT = """你是一个邮件汇总助手。请根据以下归档记录生成每日汇总报告。

归档记录：
{records}

请生成一份汇总报告，包含：
1. 总体概述
2. 重要邮件摘要
3. 需要关注的事项
4. 建议处理优先级

以 Markdown 格式返回。"""


class LLMClient:
    """OpenAI 兼容的大模型客户端。"""

    def __init__(self):
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = settings.llm_max_retries

    async def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """调用大模型 API。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]

                    if response.status_code == 429:
                        # 速率限制，等待后重试
                        logger.warning(f"Rate limited, attempt {attempt + 1}")
                        continue

                    raise LLMResponseError(
                        f"API returned status {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(f"Request timeout: {e}")
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except httpx.RequestError as e:
                last_error = LLMError(f"Request error: {e}")
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                last_error = LLMResponseError(f"Invalid response format: {e}")
                logger.error(f"Invalid response on attempt {attempt + 1}: {e}")

        raise last_error or LLMError("Unknown error after retries")

    async def extract_from_email(
        self,
        subject: str,
        sender: str,
        body: str,
    ) -> dict[str, Any]:
        """从邮件中提取结构化信息。"""
        prompt = EXTRACTION_PROMPT.format(
            subject=subject or "(无主题)",
            sender=sender or "(未知发件人)",
            body=body or "(无正文)",
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self._call_api(
                messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

            # 解析 JSON 响应
            # 尝试提取 JSON 块
            json_str = response.strip()
            if "```json" in json_str:
                start = json_str.index("```json") + 7
                end = json_str.index("```", start)
                json_str = json_str[start:end].strip()
            elif "```" in json_str:
                start = json_str.index("```") + 3
                end = json_str.index("```", start)
                json_str = json_str[start:end].strip()

            result = json.loads(json_str)

            # 验证必要字段
            required_fields = ["summary", "business_type", "priority"]
            for field in required_fields:
                if field not in result:
                    result[field] = None

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise LLMResponseError(f"Invalid JSON response: {e}") from e

    async def generate_summary(
        self,
        records: list[dict[str, Any]],
    ) -> str:
        """生成汇总报告。"""
        records_text = "\n\n".join(
            f"- 主题: {r.get('subject', 'N/A')}\n"
            f"  发件人: {r.get('sender', 'N/A')}\n"
            f"  摘要: {r.get('summary', 'N/A')}\n"
            f"  优先级: {r.get('priority', 'N/A')}\n"
            f"  风险标签: {r.get('risk_tags', [])}"
            for r in records
        )

        prompt = SUMMARY_PROMPT.format(records=records_text)
        messages = [{"role": "user", "content": prompt}]

        return await self._call_api(
            messages,
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )


# 同步版本（用于非异步环境）
class LLMClientSync:
    """同步大模型客户端。"""

    def __init__(self):
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = settings.llm_max_retries

    def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """调用大模型 API。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]

                    if response.status_code == 429:
                        logger.warning(f"Rate limited, attempt {attempt + 1}")
                        continue

                    raise LLMResponseError(
                        f"API returned status {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(f"Request timeout: {e}")
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except httpx.RequestError as e:
                last_error = LLMError(f"Request error: {e}")
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                last_error = LLMResponseError(f"Invalid response format: {e}")
                logger.error(f"Invalid response on attempt {attempt + 1}: {e}")

        raise last_error or LLMError("Unknown error after retries")

    def extract_from_email(
        self,
        subject: str,
        sender: str,
        body: str,
    ) -> dict[str, Any]:
        """从邮件中提取结构化信息。"""
        prompt = EXTRACTION_PROMPT.format(
            subject=subject or "(无主题)",
            sender=sender or "(未知发件人)",
            body=body or "(无正文)",
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self._call_api(
                messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

            json_str = response.strip()
            if "```json" in json_str:
                start = json_str.index("```json") + 7
                end = json_str.index("```", start)
                json_str = json_str[start:end].strip()
            elif "```" in json_str:
                start = json_str.index("```") + 3
                end = json_str.index("```", start)
                json_str = json_str[start:end].strip()

            result = json.loads(json_str)

            required_fields = ["summary", "business_type", "priority"]
            for field in required_fields:
                if field not in result:
                    result[field] = None

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise LLMResponseError(f"Invalid JSON response: {e}") from e

    def generate_summary(
        self,
        records: list[dict[str, Any]],
    ) -> str:
        """生成汇总报告。"""
        records_text = "\n\n".join(
            f"- 主题: {r.get('subject', 'N/A')}\n"
            f"  发件人: {r.get('sender', 'N/A')}\n"
            f"  摘要: {r.get('summary', 'N/A')}\n"
            f"  优先级: {r.get('priority', 'N/A')}\n"
            f"  风险标签: {r.get('risk_tags', [])}"
            for r in records
        )

        prompt = SUMMARY_PROMPT.format(records=records_text)
        messages = [{"role": "user", "content": prompt}]

        return self._call_api(
            messages,
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )
