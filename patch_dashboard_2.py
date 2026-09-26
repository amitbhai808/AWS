import re

with open('/Users/amitpajiyar/Desktop/AWS/vault_frontend_2/src/components/storage-dashboard.tsx', 'r') as f:
    content = f.read()

# Replace static files array with nothing (we'll pass it as prop)
content = re.sub(r'const files = \[.*?\]\n', '', content, flags=re.DOTALL)

# Add API_BASE import
content = content.replace("import { Button } from '@/components/ui/button'", "import { Button } from '@/components/ui/button'\nimport { API_BASE } from '@/lib/api'")

# Modify FileCard signature to take vault file
file_card_old = "function FileCard({ file, onShare }: { file: typeof files[number]; onShare: () => void }) {"
file_card_new = "function FileCard({ file, onShare, onRename, onDelete }: { file: any; onShare: () => void; onRename: () => void; onDelete: () => void }) {"
content = content.replace(file_card_old, file_card_new)

# Modify FileCard rendering
content = content.replace("file.name", "file.filename")
content = content.replace("file.size", "file.size_formatted")

# Map actions in FileCard
content = content.replace('<button onClick={onShare}', '<button onClick={() => { setOpen(false); onShare(); }}')
content = content.replace('<button className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"><FileText className="size-3.5" />Rename</button>',
                         '<button onClick={() => { setOpen(false); onRename(); }} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"><FileText className="size-3.5" />Rename</button>')
content = content.replace('<button className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-red-300 hover:bg-red-400/10"><X className="size-3.5" />Delete</button>',
                         '<button onClick={() => { setOpen(false); onDelete(); }} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-red-300 hover:bg-red-400/10"><X className="size-3.5" />Delete</button>')

# Add download button to FileCard
download_btn = f'<a href={{`${{API_BASE}}/files/${{file.file_id}}/download`}} download={{file.filename}} target="_blank" rel="noreferrer" className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"><Archive className="size-3.5" />Download</a>'
content = content.replace('<button onClick={() => { setOpen(false); onShare(); }}', download_btn + '<button onClick={() => { setOpen(false); onShare(); }}')


# Modify Dashboard signature
dashboard_old = "function Dashboard() {"
dashboard_new = "function Dashboard({ vaultFiles, onUploadFiles, onDelete, onShare, onRename, isUploading, activeShareUrl }: any) {"
content = content.replace(dashboard_old, dashboard_new)

# Modify Dashboard files.map
content = content.replace("{files.map((file) => <FileCard key={file.name} file={file} onShare={() => setShare(true)} />)}",
                          "{vaultFiles.map((file: any) => <FileCard key={file.file_id} file={file} onShare={() => { setShare(true); onShare(file.file_id); }} onRename={() => onRename(file.file_id, file.filename)} onDelete={() => onDelete(file.file_id)} />)}")

# Modify UploadDialog
upload_dialog_old = "function UploadDialog({ onClose }: { onClose: () => void }) {"
upload_dialog_new = "function UploadDialog({ onClose, onUploadFiles, isUploading }: { onClose: () => void, onUploadFiles: (e: any) => void, isUploading: boolean }) {"
content = content.replace(upload_dialog_old, upload_dialog_new)

# Connect file input to UploadDialog
content = content.replace('<div className="flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-cyan-300/30 bg-cyan-300/[0.03]"><UploadCloud className="mb-3 size-8 text-cyan-300" />',
                         '<div className="relative flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-cyan-300/30 bg-cyan-300/[0.03] hover:border-cyan-300 hover:bg-cyan-300/[0.05] transition-colors"><input type="file" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onChange={(e) => { onUploadFiles(e); onClose(); }} disabled={isUploading} /><UploadCloud className="mb-3 size-8 text-cyan-300" />')

# Hide fake file in UploadDialog
content = content.replace('<div className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">', '{isUploading && <div className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">')
content = content.replace('75%</span></div></div>', 'Uploading...</span></div></div>}')

content = content.replace('<Button className="bg-cyan-300 text-[#071014] hover:bg-cyan-200" onClick={onClose}>Upload files</Button>', '')
content = content.replace('{upload && <UploadDialog onClose={() => setUpload(false)} />}', '{upload && <UploadDialog onClose={() => setUpload(false)} onUploadFiles={onUploadFiles} isUploading={isUploading} />}')

# Modify ShareDialog
share_dialog_old = "function ShareDialog({ onClose }: { onClose: () => void }) {"
share_dialog_new = "function ShareDialog({ onClose, activeShareUrl }: { onClose: () => void, activeShareUrl: string }) {"
content = content.replace(share_dialog_old, share_dialog_new)
content = content.replace('vault.io/s/8f2kLmQ', '{activeShareUrl}')

content = content.replace('{share && <ShareDialog onClose={() => setShare(false)} />}', '{share && <ShareDialog onClose={() => setShare(false)} activeShareUrl={activeShareUrl} />}')


# Write back
with open('/Users/amitpajiyar/Desktop/AWS/vault_frontend_2/src/components/storage-dashboard.tsx', 'w') as f:
    f.write(content)
