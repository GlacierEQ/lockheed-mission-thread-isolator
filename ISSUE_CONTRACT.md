# ISSUE CONTRACT

## Pain
Cross-mission shared state lets one thread poison another; authority tokens bleed across contexts.

## Non-goals
- Distributed multi-node isolation
- Classified operational systems

## Success
- Direct cross-thread reads impossible
- Import only via export grant IDs
- Bad authority fails closed
