# Driver Document Verification Workflow

## Overview
The system implements a multi-stage driver verification process to ensure compliance and safety.

## Driver Verification States

| State | Description | Actions Available |
|-------|-------------|-------------------|
| `pending` | Documents uploaded, awaiting admin review | Admin: Approve/Reject |
| `approved` | All documents verified and accepted | Driver: Can accept rides |
| `rejected` | Documents did not meet requirements | Driver: Re-upload and resubmit |

## Document Types Required

1. **License** (`license_url`) - Valid driving license
2. **Aadhaar** (`aadhar_url`) - Government ID proof
3. **RC (Registration Certificate)** (`rc_url`) - Vehicle registration
4. **Insurance** (`insurance_url`) - Valid vehicle insurance

## API Endpoints

### Admin: Update Driver Verification Status

**PATCH** `/api/admin/drivers/{driver_id}`

Request body:
```json
{
  "doc_status": "approved",  // or "rejected"
  "is_verified": true
}
```

Response:
```json
{
  "ok": true
}
```

### Admin: List Drivers Pending Verification

**GET** `/api/admin/drivers`

Returns all drivers with their current `doc_status`:
- `pending`: Awaiting approval
- `approved`: Verified
- `rejected`: Needs resubmission

### Driver: Submit Documents (Existing Endpoint)

**PATCH** `/api/drivers/me`

Request body:
```json
{
  "license_url": "https://...",
  "aadhar_url": "https://...",
  "rc_url": "https://...",
  "insurance_url": "https://..."
}
```

## Workflow Diagram

```
Driver Profile Creation
        ↓
    [pending] ← Driver submits documents
        ↓
   Admin Review (in admin dashboard)
        ↓
    Approved → Driver can accept rides → is_verified = true
        ↓
    Rejected → Driver gets notification → Can re-upload
```

## WebSocket Notifications

When a driver's verification status changes:
- **Event**: `driver_verified` or `driver_rejected`
- **Broadcast**: Sent to individual driver via WebSocket
- **Payload**: `{ status: "approved"|"rejected", message: "..." }`

## Implementation Notes

1. Documents are stored as URLs (typically to cloud storage like S3)
2. Admin dashboard displays driver list with verification status
3. Verification history can be tracked via created_at field updates
4. Future: Add automated document validation (OCR, NLP)
5. Future: Email notifications to drivers on approval/rejection

## Security Considerations

- URLs must be HTTPS for compliance
- Driver's email is masked in logs (PII protection)
- Document URLs should be private/authenticated
- Admins can only approve/reject, not delete documents
