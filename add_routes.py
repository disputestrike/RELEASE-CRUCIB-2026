#!/usr/bin/env python3
"""
Automatically add @app decorators to all backend functions in server.py
"""
import re

# Read the file
with open('backend/server.py', 'r') as f:
    content = f.read()

# Define all routes to add with their decorators
routes = {
    # Payment & Billing
    'get_bundles': ('@app.get("/tokens/bundles")', 'GET'),
    'purchase_tokens': ('@app.post("/tokens/purchase")', 'POST'),
    'get_token_history': ('@app.get("/tokens/history")', 'GET'),
    'get_token_usage': ('@app.get("/tokens/usage")', 'GET'),
    
    # Referrals
    'get_referral_code': ('@app.get("/referrals/code")', 'GET'),
    'get_referral_stats': ('@app.get("/referrals/stats")', 'GET'),
    
    # Agents - Individual
    'get_agents': ('@app.get("/agents")', 'GET'),
    'get_agent_status': ('@app.get("/agents/{project_id}/status")', 'GET'),
    'agent_planner': ('@app.post("/agents/planner")', 'POST'),
    'agent_requirements_clarifier': ('@app.post("/agents/requirements-clarifier")', 'POST'),
    'agent_stack_selector': ('@app.post("/agents/stack-selector")', 'POST'),
    'agent_backend_generate': ('@app.post("/agents/backend-generate")', 'POST'),
    'agent_database_design': ('@app.post("/agents/database-design")', 'POST'),
    'agent_api_integrate': ('@app.post("/agents/api-integrate")', 'POST'),
    'agent_test_generate': ('@app.post("/agents/test-generate")', 'POST'),
    'agent_image_generate': ('@app.post("/agents/image-generate")', 'POST'),
    'agent_test_executor': ('@app.post("/agents/test-executor")', 'POST'),
    'agent_deploy': ('@app.post("/agents/deploy")', 'POST'),
    'agent_memory_store': ('@app.post("/agents/memory/store")', 'POST'),
    'agent_memory_list': ('@app.get("/agents/memory/list")', 'GET'),
    'agent_export_pdf': ('@app.post("/agents/export/pdf")', 'POST'),
    'agent_export_excel': ('@app.post("/agents/export/excel")', 'POST'),
    'agent_export_markdown': ('@app.post("/agents/export/markdown")', 'POST'),
    'agent_scrape': ('@app.post("/agents/scrape")', 'POST'),
    'agent_automation': ('@app.post("/agents/automation")', 'POST'),
    'agent_automation_list': ('@app.get("/agents/automation/list")', 'GET'),
    'agent_design': ('@app.post("/agents/design")', 'POST'),
    'agent_layout': ('@app.post("/agents/layout")', 'POST'),
    'agent_seo': ('@app.post("/agents/seo")', 'POST'),
    'agent_content': ('@app.post("/agents/content")', 'POST'),
    'agent_brand': ('@app.post("/agents/brand")', 'POST'),
    'agent_documentation': ('@app.post("/agents/documentation")', 'POST'),
    'agent_validation': ('@app.post("/agents/validation")', 'POST'),
    'agent_auth_setup': ('@app.post("/agents/auth-setup")', 'POST'),
    'agent_payment_setup': ('@app.post("/agents/payment-setup")', 'POST'),
    'agent_monitoring': ('@app.post("/agents/monitoring")', 'POST'),
    'agent_accessibility': ('@app.post("/agents/accessibility")', 'POST'),
    'agent_devops': ('@app.post("/agents/devops")', 'POST'),
    'agent_webhook': ('@app.post("/agents/webhook")', 'POST'),
    'agent_email': ('@app.post("/agents/email")', 'POST'),
    'agent_legal_compliance': ('@app.post("/agents/legal-compliance")', 'POST'),
    'agent_run_generic': ('@app.post("/agents/run")', 'POST'),
    
    # Agent CRUD
    'agents_create': ('@app.post("/agents/create")', 'POST'),
    'agents_list': ('@app.get("/agents/list")', 'GET'),
    'agents_template_get': ('@app.get("/agents/templates/{slug}")', 'GET'),
    'agents_get': ('@app.get("/agents/{agent_id}")', 'GET'),
    'agents_webhook_rotate_secret': ('@app.post("/agents/{agent_id}/webhook/rotate-secret")', 'POST'),
    'agents_update': ('@app.put("/agents/{agent_id}")', 'PUT'),
    'agents_delete': ('@app.delete("/agents/{agent_id}")', 'DELETE'),
    'agents_runs_list': ('@app.get("/agents/{agent_id}/runs")', 'GET'),
    'agents_run_get': ('@app.get("/agents/runs/{run_id}")', 'GET'),
    'agents_run_logs': ('@app.get("/agents/runs/{run_id}/logs")', 'GET'),
    
    # Projects
    'projects_create': ('@app.post("/projects/create")', 'POST'),
    'projects_list': ('@app.get("/projects")', 'GET'),
    'projects_get': ('@app.get("/projects/{project_id}")', 'GET'),
    'projects_update': ('@app.put("/projects/{project_id}")', 'PUT'),
    'projects_delete': ('@app.delete("/projects/{project_id}")', 'DELETE'),
    'projects_share': ('@app.post("/projects/{project_id}/share")', 'POST'),
    'projects_get_logs': ('@app.get("/projects/{project_id}/logs")', 'GET'),
    
    # Users
    'users_get_profile': ('@app.get("/users/profile")', 'GET'),
    'users_update_profile': ('@app.put("/users/profile")', 'PUT'),
    'users_change_password': ('@app.post("/users/password/change")', 'POST'),
    
    # MFA
    'mfa_setup': ('@app.post("/auth/mfa/setup")', 'POST'),
    'mfa_verify': ('@app.post("/auth/mfa/verify")', 'POST'),
    'mfa_disable': ('@app.post("/auth/mfa/disable")', 'POST'),
    'mfa_status': ('@app.get("/auth/mfa/status")', 'GET'),
    'mfa_backup_code_use': ('@app.post("/auth/mfa/backup-code/use")', 'POST'),
    'mfa_get_backup_codes': ('@app.get("/auth/mfa/backup-codes")', 'GET'),
    'mfa_regenerate_backup_codes': ('@app.post("/auth/mfa/backup-codes/regenerate")', 'POST'),
    
    # Workspace & Environment
    'get_workspace_env': ('@app.get("/workspace/env")', 'GET'),
    'set_workspace_env': ('@app.post("/workspace/env")', 'POST'),
    'create_workspace_api_key': ('@app.post("/workspace/api-keys")', 'POST'),
    'delete_workspace_api_key': ('@app.delete("/workspace/api-keys/{key_id}")', 'DELETE'),
    
    # Admin
    'admin_get_users': ('@app.get("/admin/users")', 'GET'),
    'admin_ban_user': ('@app.post("/admin/users/{user_id}/ban")', 'POST'),
    'admin_reset_password': ('@app.post("/admin/users/{user_id}/reset-password")', 'POST'),
    'admin_get_metrics': ('@app.get("/admin/metrics")', 'GET'),
    'admin_get_alerts': ('@app.get("/admin/alerts")', 'GET'),
    
    # Chat & History
    'save_chat_session': ('@app.post("/chat/save")', 'POST'),
    'get_chat_history': ('@app.get("/chat/history")', 'GET'),
    
    # Templates & Examples
    'get_examples': ('@app.get("/examples")', 'GET'),
    'save_template': ('@app.post("/templates/save")', 'POST'),
    'list_templates': ('@app.get("/templates")', 'GET'),
    
    # Prompts & Exports
    'save_prompt': ('@app.post("/prompts/save")', 'POST'),
    'list_prompts': ('@app.get("/prompts")', 'GET'),
    'get_exports': ('@app.get("/exports")', 'GET'),
    
    # Notifications
    'get_notifications': ('@app.get("/notifications")', 'GET'),
    
    # Enterprise
    'enterprise_contact': ('@app.post("/enterprise/contact")', 'POST'),
}

# Process the file line by line
lines = content.split('\n')
new_lines = []
i = 0
added_count = 0

while i < len(lines):
    line = lines[i]
    
    # Check if this line is an async def that needs a decorator
    match = re.match(r'^async def ([a-z_][a-z0-9_]*)\(', line)
    if match:
        func_name = match.group(1)
        if func_name in routes:
            decorator, method = routes[func_name]
            # Add the decorator before the function
            new_lines.append(decorator)
            added_count += 1
    
    new_lines.append(line)
    i += 1

# Write the modified content
with open('backend/server.py', 'w') as f:
    f.write('\n'.join(new_lines))

print(f"✅ Added {added_count} @app decorators to server.py")
print(f"Total lines: {len(new_lines)}")

