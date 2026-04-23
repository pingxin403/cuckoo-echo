# Conversation Export API

## Problem / 问题

Enterprise customers require bulk conversation export for:
- Compliance audits (GDPR data portability, CCPA)
- Legal discovery
- Internal analytics
- Migration off the platform

Currently there is no bulk export API for conversations.

## Background / 背景

- Individual conversation retrieval exists via admin API
- No bulk导出 endpoint exists
- Knowledge export is handled separately

Enterprise compliance requirements:
- Data must be exportable in standard formats (JSON, CSV)
- Must support date range filtering
- Must support pagination for large exports
- Must be auditable (admin only)

## Requirements / 需求

1. **Bulk Export Endpoint**
   - `POST /admin/v1/conversations/export`
   - Support date range filtering
   - Support pagination
   - Return async job for large datasets

2. **Export Formats**
   - JSON (full fidelity)
   - CSV (tabular summary)
   - Markdown (readable)

3. **Filtering Options**
   - By tenant_id
   - By date range (start_date, end_date)
   - By status (active, closed)
   - By message count

4. **Async Export for Large Datasets**
   - Return job_id immediately
   - Poll for completion
   - Download when ready

5. **Export Audit Trail**
   - Log all export requests
   - Include metadata in export

## Implementation / 实现方案

```python
# admin_service/routes/conversations.py
@router.post("/export")
async def export_conversations(
    request: Request,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    format: str = "json",
):
    # Create export job
    job = await create_export_job(
        tenant_id=get_tenant_id(request),
        filters={"start_date": start_date, "end_date": end_date},
        format=format,
    )
    
    if estimated_rows > 1000:
        return {"job_id": job.id, "status": "processing"}
    
    # Synchronous export for small datasets
    data = await generate_export(job)
    return {"data": data}
```

## Acceptance Criteria / 验收标准

- [ ] POST /admin/v1/conversations/export returns with date filtering
- [ ] JSON format exports full conversation
- [ ] CSV format exports tabular summary
- [ ] Large exports use async job pattern
- [ ] Export audit trail created
- [ ] Pagination works correctly
- [ ] Only tenant-owned conversations exported (RLS)