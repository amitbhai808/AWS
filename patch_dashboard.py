import re

with open('/Users/amitpajiyar/Desktop/AWS/vault_frontend_2/src/components/storage-dashboard.tsx', 'r') as f:
    content = f.read()

# Make UserButton available
content = content.replace("import { Button } from '@/components/ui/button'", "import { Button } from '@/components/ui/button'\nimport { UserButton } from '@clerk/nextjs'")

# Replace dummy JD profile with UserButton in Header
header_match = re.search(r'<div className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-200 to-orange-500 text-xs font-bold text-\[\#31200b\]">JD</div><div className="hidden text-left sm:block"><div className="text-xs font-medium text-zinc-200">Jordan Davis</div><div className="text-\[10px\] text-zinc-600">Pro workspace</div></div><ChevronDown className="hidden size-3.5 text-zinc-600 sm:block" />', content)
if header_match:
    content = content.replace(header_match.group(0), '<UserButton />')

# Write back
with open('/Users/amitpajiyar/Desktop/AWS/vault_frontend_2/src/components/storage-dashboard.tsx', 'w') as f:
    f.write(content)
