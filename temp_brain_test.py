from backend.services.brain_layer import BrainLayer
from backend.services.conversation_manager import ContextManager

brain = BrainLayer()
cm = ContextManager()
session = cm.create_session('test')

prompts = [
    'Build me a stunning multi-page website for an AI automation company with hero, features, pricing, testimonials, FAQ, contact page, and footer. Use a clean modern premium style.',
    'Make the design more like a premium Silicon Valley startup. Tighten spacing, improve typography, and make the pricing section much stronger.',
    'Build me a platform for coaches.',
    'Continue, but fix anything broken and make sure mobile looks polished.',
    'Build a production-ready SaaS landing page with authentication flow screens, dashboard preview, pricing, and waitlist capture.',
    'Do not restart. Keep the current build, but improve typography, spacing, CTA copy, and the visual hierarchy.',
]

print('--- SIMULATION ---')
for prompt in prompts:
    result = brain.assess_request(session, prompt)
    print('PROMPT:', prompt)
    print('RESPONSE:', result['assistant_response'])
    print('SUGGESTIONS:', result.get('suggestions'))
    print('SELECTED_AGENTS:', result.get('selected_agents'))
    print('INTENT:', result.get('intent'), 'CONF:', result.get('intent_confidence'))
    print('-' * 80)
