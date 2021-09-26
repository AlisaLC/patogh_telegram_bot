CHAT_ID=12345 # Use @username_to_id_bot to find the chat ID
TOKEN="token"
mysqldump --databases patogh | gzip > backup.sql.gz
curl -X POST -H "content-type: multipart/form-data" -F document=@"backup.sql.gz" -F chat_id="$CHAT_ID" "https://api.telegram.org/bot$TOKEN/sendDocument"
rm backup.sql.gz
