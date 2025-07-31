# This file has been consolidated into stores.models
# All tenant functionality is now part of the unified Store model
# This eliminates the duplication between Tenant and Store models

# Migration: All Tenant references should be updated to Store
# The Store model now handles:
# - Multi-tenancy through schema_name field
# - Domain management through StoreDomain model  
# - All business logic previously in Tenant

# To maintain backward compatibility during migration:
# 1. Create data migration to copy Tenant data to Store
# 2. Update all foreign keys from Tenant to Store
# 3. Remove this file after migration is complete

pass
