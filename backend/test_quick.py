#!/usr/bin/env python
"""Quick validation test for BuildContract."""

from orchestration.build_contract import BuildContract

def test_basic_functionality():
    # Test 1: Create contract
    contract = BuildContract(
        build_id='test-123',
        build_class='saas',
        product_name='Test',
        original_goal='Test'
    )
    print(f'[OK] Contract created: {contract.build_id}')
    
    # Test 2: Update progress
    contract.update_progress('required_files', 'file1.tsx', done=True)
    percent = contract.contract_progress["required_files"]["percent"]
    print(f'[OK] Progress updated: {percent}%')
    
    # Test 3: Check satisfaction
    is_satisfied = contract.is_satisfied()
    print(f'[OK] is_satisfied() returns: {is_satisfied}')
    
    # Test 4: Freeze
    contract.freeze()
    assert contract.status == 'frozen'
    print('[OK] Contract frozen')
    
    print('\nAll core tests passed!')

if __name__ == "__main__":
    test_basic_functionality()
