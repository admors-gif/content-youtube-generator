#!/bin/bash
# Test the /produce endpoint
cat > /tmp/produce_test.json << 'EOF'
{"projectId":"3N2sQDJsHxrU4nwazdue"}
EOF
curl -s -X POST http://localhost:8085/produce -H "Content-Type: application/json" -d @/tmp/produce_test.json
echo ""
echo "Done."
