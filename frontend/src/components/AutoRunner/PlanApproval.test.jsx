import React from 'react';
import { render, screen } from '@testing-library/react';
import PlanApproval from './PlanApproval';

const basePlan = {
  goal: 'Build something',
  build_kind: 'standard',
  estimated_steps: 4,
  phases: [],
  risk_flags: ['goal_spec_nextjs_autorunner_template_is_vite_react'],
  crucib_build_target: 'api_backend',
};

describe('PlanApproval', () => {
  test('spec gap copy is API-first when execution target is api_backend', () => {
    render(
      <PlanApproval
        plan={basePlan}
        estimate={null}
        capabilityNotice={[]}
        buildTargetMeta={{
          id: 'api_backend',
          label: 'API & backend-first',
          tagline: 'API track',
          guarantees: [],
          on_this_run: [],
          roadmap: [],
        }}
        onApprove={() => {}}
        onEdit={() => {}}
        onRunAuto={() => {}}
        loading={false}
      />,
    );
    expect(screen.getByText('Full pipeline — run never blocked')).toBeInTheDocument();
    expect(screen.getByText(/Python API routes/)).toBeInTheDocument();
    expect(screen.queryByText(/fixed scaffold/)).not.toBeInTheDocument();
  });

  test('spec gap copy mentions Vite stack for vite_react target', () => {
    render(
      <PlanApproval
        plan={{
          ...basePlan,
          crucib_build_target: 'vite_react',
          risk_flags: ['goal_spec_orm_autorunner_writes_sql_sketch_not_orm'],
        }}
        estimate={null}
        capabilityNotice={[]}
        buildTargetMeta={{
          id: 'vite_react',
          label: 'Full-stack web (Vite + React)',
          tagline: 'Default',
          guarantees: [],
          on_this_run: [],
          roadmap: [],
        }}
        onApprove={() => {}}
        onEdit={() => {}}
        onRunAuto={() => {}}
        loading={false}
      />,
    );
    expect(screen.getByText(/Vite \+ React/)).toBeInTheDocument();
  });
});
