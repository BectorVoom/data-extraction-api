# rest_api_duckdb/app/services/claude_analyzer.py
# Claude Code integration for automated error analysis

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Claude Code integration configuration
CLAUDE_CONFIG = {
    "api_key": os.getenv("CLAUDE_API_KEY"),
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1000,
    "temperature": 0.1  # Low temperature for consistent analysis
}

class ClaudeAnalyzer:
    """
    Service for analyzing errors using Claude Code
    
    This service provides automated analysis of client-side errors,
    focusing on Excel Add-in specific issues and providing actionable insights.
    """
    
    def __init__(self):
        self.api_key = CLAUDE_CONFIG["api_key"]
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Claude Code integration disabled: CLAUDE_API_KEY not found")
    
    def _create_analysis_prompt(self, error_payload: Dict[str, Any], classifications: List[str]) -> str:
        """Create a structured prompt for Claude Code analysis"""
        
        prompt = f"""You are a technical support specialist analyzing errors from an Excel Add-in application. 

Error Details:
- Type: {error_payload.get('type')}
- Classifications: {', '.join(classifications)}
- Message: {error_payload.get('message', 'N/A')}
- Timestamp: {error_payload.get('timestamp', 'N/A')}

Context Information:
"""
        
        # Add Office.js context if available
        if error_payload.get('office_context'):
            office_ctx = error_payload['office_context']
            prompt += f"""
Office Context:
- Host: {office_ctx.get('host', 'unknown')}
- Platform: {office_ctx.get('platform', 'unknown')}
- Version: {office_ctx.get('version', 'unknown')}
"""
        
        # Add Excel context if available
        if error_payload.get('excel_context'):
            excel_ctx = error_payload['excel_context']
            prompt += f"""
Excel Context:
- Workbook Available: {excel_ctx.get('hasWorkbook', 'unknown')}
- Worksheet Count: {excel_ctx.get('worksheetCount', 'unknown')}
"""
        
        # Add operation context if available
        if error_payload.get('operation'):
            prompt += f"""
Failed Operation: {error_payload['operation']}
"""
        
        # Add API context if available
        if error_payload.get('endpoint'):
            prompt += f"""
API Endpoint: {error_payload['endpoint']}
"""
        
        # Add stack trace if available (truncated for brevity)
        if error_payload.get('stack'):
            stack = error_payload['stack'][:1000] + "..." if len(error_payload['stack']) > 1000 else error_payload['stack']
            prompt += f"""
Stack Trace (partial):
{stack}
"""
        
        prompt += """

Please provide analysis in JSON format with the following structure:
{
  "severity": "low|medium|high|critical",
  "category": "excel_integration|api_communication|validation|javascript|office_environment",
  "root_cause_hypotheses": [
    "hypothesis 1 (1-2 sentences)",
    "hypothesis 2 (1-2 sentences)",
    "hypothesis 3 (1-2 sentences)"
  ],
  "debugging_steps": [
    "step 1",
    "step 2", 
    "step 3"
  ],
  "potential_fixes": [
    "fix 1 with explanation",
    "fix 2 with explanation"
  ],
  "prevention_suggestions": [
    "prevention 1",
    "prevention 2"
  ],
  "additional_info_needed": [
    "info 1",
    "info 2"
  ]
}

Focus on:
1. Excel Add-in specific issues (Office.js, worksheet operations, context sync)
2. API communication problems (CORS, HTTPS, network issues)
3. Data validation and format issues
4. User experience improvements
5. Production deployment considerations

Be concise and actionable. Prioritize solutions that can be implemented quickly.
"""
        
        return prompt
    
    async def analyze_error(self, error_payload: Dict[str, Any], classifications: List[str]) -> Optional[Dict[str, Any]]:
        """
        Analyze an error using Claude Code
        
        Args:
            error_payload: Error details from client
            classifications: List of error classifications
            
        Returns:
            Analysis results or None if analysis fails
        """
        
        if not self.enabled:
            logger.debug("Claude Code analysis skipped: not enabled")
            return None
        
        try:
            # Note: This is a placeholder for the actual Claude Code SDK integration
            # The actual implementation would depend on the specific Claude Code SDK
            
            prompt = self._create_analysis_prompt(error_payload, classifications)
            
            # Placeholder for Claude Code API call
            # In the actual implementation, this would be something like:
            # 
            # from anthropic import Anthropic
            # client = Anthropic(api_key=self.api_key)
            # response = await client.messages.create(
            #     model=CLAUDE_CONFIG["model"],
            #     max_tokens=CLAUDE_CONFIG["max_tokens"],
            #     temperature=CLAUDE_CONFIG["temperature"],
            #     messages=[{"role": "user", "content": prompt}]
            # )
            # analysis_text = response.content[0].text
            
            # For now, return a mock analysis structure
            mock_analysis = {
                "analysis_id": f"claude_analysis_{error_payload.get('errorId', 'unknown')}",
                "timestamp": datetime.now().isoformat(),
                "error_id": error_payload.get('errorId'),
                "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "analysis": {
                    "severity": self._estimate_severity(error_payload, classifications),
                    "category": self._categorize_error(classifications),
                    "root_cause_hypotheses": self._generate_hypotheses(error_payload, classifications),
                    "debugging_steps": self._suggest_debugging_steps(error_payload, classifications),
                    "potential_fixes": self._suggest_fixes(error_payload, classifications),
                    "prevention_suggestions": self._suggest_prevention(error_payload, classifications),
                    "additional_info_needed": self._identify_missing_info(error_payload)
                },
                "metadata": {
                    "model_used": CLAUDE_CONFIG["model"],
                    "temperature": CLAUDE_CONFIG["temperature"],
                    "classifications": classifications
                }
            }
            
            logger.info(f"Claude analysis completed for error {error_payload.get('errorId')}")
            return mock_analysis
            
        except Exception as e:
            logger.error(f"Claude Code analysis failed: {e}")
            return None
    
    def _estimate_severity(self, error_payload: Dict[str, Any], classifications: List[str]) -> str:
        """Estimate error severity based on type and context"""
        
        message = error_payload.get('message', '').lower()
        
        # Critical errors
        if any(keyword in message for keyword in ['context.sync failed', 'office.js not available', 'workbook not found']):
            return "critical"
        
        # High severity errors
        if 'excel_error' in classifications and any(keyword in message for keyword in ['permission', 'access denied', 'authorization']):
            return "high"
        
        # Medium severity errors
        if any(classification in classifications for classification in ['api_error', 'validation_error']):
            return "medium"
        
        # Default to low
        return "low"
    
    def _categorize_error(self, classifications: List[str]) -> str:
        """Categorize error for analysis"""
        
        if 'excel_error' in classifications:
            return "excel_integration"
        elif 'api_error' in classifications:
            return "api_communication"
        elif 'validation_error' in classifications:
            return "validation"
        elif 'javascript_error' in classifications:
            return "javascript"
        else:
            return "office_environment"
    
    def _generate_hypotheses(self, error_payload: Dict[str, Any], classifications: List[str]) -> List[str]:
        """Generate root cause hypotheses"""
        
        hypotheses = []
        message = error_payload.get('message', '').lower()
        
        if 'excel_error' in classifications:
            if 'context.sync' in message:
                hypotheses.append("Excel context synchronization failed, possibly due to network latency or large data operations")
            if 'permission' in message or 'access' in message:
                hypotheses.append("Insufficient permissions for Excel operations, user may need to grant additional access")
            if 'workbook' in message:
                hypotheses.append("Workbook state issue, possibly caused by user switching between workbooks during operation")
        
        if 'api_error' in classifications:
            if 'cors' in message or 'cross-origin' in message:
                hypotheses.append("CORS configuration issue preventing API communication from Excel Add-in")
            if 'timeout' in message or 'network' in message:
                hypotheses.append("Network connectivity issue or API server performance problem")
            if 'https' in message or 'ssl' in message:
                hypotheses.append("HTTPS certificate or SSL configuration issue")
        
        if 'validation_error' in classifications:
            hypotheses.append("User input validation failed, possibly due to unclear UI guidance or data format expectations")
            
        # Default hypothesis if none others apply
        if not hypotheses:
            hypotheses.append("Unexpected application state or environment-specific configuration issue")
        
        return hypotheses
    
    def _suggest_debugging_steps(self, error_payload: Dict[str, Any], classifications: List[str]) -> List[str]:
        """Suggest debugging steps"""
        
        steps = []
        
        if 'excel_error' in classifications:
            steps.extend([
                "Check Excel Add-in permissions and trust settings",
                "Verify Office.js library version compatibility",
                "Test with a fresh workbook and minimal data"
            ])
        
        if 'api_error' in classifications:
            steps.extend([
                "Test API endpoint directly with curl or Postman",
                "Check browser developer console for CORS errors",
                "Verify API server logs for request details"
            ])
        
        if 'validation_error' in classifications:
            steps.extend([
                "Review input validation rules and error messages",
                "Test with various input formats and edge cases",
                "Check for client-server validation consistency"
            ])
        
        # Always include basic debugging steps
        steps.extend([
            "Reproduce error in Excel Online vs Desktop",
            "Check browser version and Add-in manifest compatibility"
        ])
        
        return steps
    
    def _suggest_fixes(self, error_payload: Dict[str, Any], classifications: List[str]) -> List[str]:
        """Suggest potential fixes"""
        
        fixes = []
        message = error_payload.get('message', '').lower()
        
        if 'excel_error' in classifications:
            if 'context.sync' in message:
                fixes.append("Add retry logic with exponential backoff for context.sync operations")
            fixes.append("Implement proper error handling for Excel API calls with user-friendly messages")
            fixes.append("Add checks for Office.js availability before calling Excel APIs")
        
        if 'api_error' in classifications:
            fixes.append("Update CORS configuration to include Excel Add-in origins")
            fixes.append("Implement request timeout handling and retry mechanisms")
            fixes.append("Add API health checks and fallback endpoints")
        
        if 'validation_error' in classifications:
            fixes.append("Improve input validation with real-time feedback")
            fixes.append("Add input format examples and better error messages")
        
        return fixes
    
    def _suggest_prevention(self, error_payload: Dict[str, Any], classifications: List[str]) -> List[str]:
        """Suggest prevention measures"""
        
        prevention = [
            "Implement comprehensive error monitoring and alerting",
            "Add automated testing for Excel Add-in scenarios",
            "Create user documentation for common error scenarios"
        ]
        
        if 'excel_error' in classifications:
            prevention.extend([
                "Add Office.js error handling training for development team",
                "Implement graceful degradation for Excel API failures"
            ])
        
        if 'api_error' in classifications:
            prevention.extend([
                "Set up API monitoring and health checks",
                "Implement API rate limiting and abuse protection"
            ])
        
        return prevention
    
    def _identify_missing_info(self, error_payload: Dict[str, Any]) -> List[str]:
        """Identify additional information that would help analysis"""
        
        missing_info = []
        
        if not error_payload.get('office_context'):
            missing_info.append("Office.js context information (host, platform, version)")
        
        if not error_payload.get('excel_context'):
            missing_info.append("Excel-specific context (workbook state, worksheet count)")
        
        if not error_payload.get('stack'):
            missing_info.append("Complete stack trace for JavaScript errors")
        
        if error_payload.get('type') == 'api_error' and not error_payload.get('endpoint'):
            missing_info.append("Specific API endpoint that failed")
        
        if error_payload.get('type') == 'excel_error' and not error_payload.get('operation'):
            missing_info.append("Specific Excel operation that failed")
        
        missing_info.extend([
            "User reproduction steps",
            "Network environment details (corporate proxy, firewall)",
            "Excel version and platform details"
        ])
        
        return missing_info

# Global analyzer instance
claude_analyzer = ClaudeAnalyzer()