
import json, os, uuid, datetime, boto3
s3 = boto3.client('s3')
BUCKET = os.environ.get('BUCKET', 'vgnshlvnz-job-tracker')

def _app_prefix(app_id):
    year = app_id.split('_')[1].split('-')[0]
    return f"applications/{year}/{app_id}/"

def lambda_handler(event, context):
    method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
    path = event.get('path') or event.get('requestContext', {}).get('http', {}).get('path', '')
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    # POST /applications
    if method == 'POST' and path == '/applications':
        body = json.loads(event.get('body') or '{}')
        app_id = f"app_{datetime.date.today()}_{uuid.uuid4().hex[:4]}"
        prefix = _app_prefix(app_id)
        meta = {
            "application_id": app_id,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "applied",
            **body,
            "cv_key": f"{prefix}cv.pdf"
        }
        s3.put_object(
            Bucket=BUCKET,
            Key=f"{prefix}meta.json",
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode(),
            ContentType="application/json"
        )
        url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={"Bucket": BUCKET, "Key": meta["cv_key"], "ContentType": "application/pdf"},
            ExpiresIn=900
        )
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"application_id": app_id, "cv_upload_url": url})}

    # GET /applications/{id}
    if method == 'GET' and path.startswith('/applications/'):
        app_id = path.split('/')[-1]
        key = f"{_app_prefix(app_id)}meta.json"
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        meta = json.loads(obj['Body'].read())
        dl = s3.generate_presigned_url('get_object', Params={"Bucket": BUCKET, "Key": meta["cv_key"]}, ExpiresIn=900)
        meta["cv_download_url"] = dl
        return {"statusCode": 200, "headers": headers, "body": json.dumps(meta)}

    # GET /applications
    if method == 'GET' and path == '/applications':
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="applications/", Delimiter="/", MaxKeys=100)
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"todo":"implement pagination"})}

    # PUT /applications/{id}
    if method == 'PUT' and path.startswith('/applications/'):
        app_id = path.split('/')[-1]
        body = json.loads(event.get('body') or '{}')
        key = f"{_app_prefix(app_id)}meta.json"
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        meta = json.loads(obj['Body'].read())
        meta.update(body)
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode(),
            ContentType="application/json"
        )
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"application_id": app_id, "updated": True})}

    # POST /applications/{id}/cv-upload-url
    if method == 'POST' and path.startswith('/applications/') and path.endswith('/cv-upload-url'):
        app_id = path.split('/')[2]
        key = f"{_app_prefix(app_id)}cv.pdf"
        url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={"Bucket": BUCKET, "Key": key, "ContentType": "application/pdf"},
            ExpiresIn=900
        )
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"cv_upload_url": url})}

    return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Endpoint not found"})}
