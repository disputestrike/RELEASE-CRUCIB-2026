" CrucibAI Vim/Neovim Plugin
" 115-agent autonomous code generation for Vim/Neovim
" Installation: Place in ~/.vim/plugin/ or ~/.config/nvim/plugin/

if exists('g:crucibai_loaded')
    finish
endif
let g:crucibai_loaded = 1

" Configuration
let g:crucibai_api_url = get(g:, 'crucibai_api_url', 'http://localhost:8000')
let g:crucibai_api_key = get(g:, 'crucibai_api_key', '')
let g:crucibai_auto_analyze = get(g:, 'crucibai_auto_analyze', 1)
let g:crucibai_enable_voice = get(g:, 'crucibai_enable_voice', 1)

" Commands
command! CrucibaiGenerateCode call crucibai#generate_code()
command! CrucibaiQuickFix call crucibai#quick_fix()
command! CrucibaiAnalyzeVibe call crucibai#analyze_vibe()
command! CrucibaiVoiceInput call crucibai#voice_input()
command! CrucibaiGenerateTests call crucibai#generate_tests()
command! CrucibaiRefactor call crucibai#refactor()
command! CrucibaiGenerateDocs call crucibai#generate_docs()
command! CrucibaiSettings call crucibai#show_settings()
command! CrucibaiStatus call crucibai#show_status()

" Keybindings
nnoremap <silent> <leader>cg :CrucibaiGenerateCode<CR>
nnoremap <silent> <leader>cf :CrucibaiQuickFix<CR>
nnoremap <silent> <leader>cv :CrucibaiAnalyzeVibe<CR>
nnoremap <silent> <leader>ci :CrucibaiVoiceInput<CR>
nnoremap <silent> <leader>ct :CrucibaiGenerateTests<CR>
nnoremap <silent> <leader>cr :CrucibaiRefactor<CR>
nnoremap <silent> <leader>cd :CrucibaiGenerateDocs<CR>

" Autocommands
if g:crucibai_auto_analyze
    augroup crucibai
        autocmd!
        autocmd BufWritePost * call crucibai#analyze_file()
    augroup END
endif
