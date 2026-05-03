" CrucibAI Autoload Module
" Core functionality for Vim/Neovim plugin

" Generate code
function! crucibai#generate_code()
    let prompt = input('Describe what to generate: ')
    if empty(prompt)
        return
    endif

    call crucibai#_show_status('Generating code...')

    let context = join(getline(1, '$'), '\n')
    let language = &filetype

    let data = {
        \ 'prompt': prompt,
        \ 'context': context,
        \ 'language': language
    \ }

    call crucibai#_make_request('POST', '/api/generate', data, function('crucibai#_on_generate_done'))
endfunction

" Quick fix code issues
function! crucibai#quick_fix()
    let selected = crucibai#_get_selected_text()
    if empty(selected)
        echo 'Select code to fix'
        return
    endif

    call crucibai#_show_status('Fixing code...')

    let language = &filetype
    let data = {
        \ 'code': selected,
        \ 'language': language
    \ }

    call crucibai#_make_request('POST', '/api/fix', data, function('crucibai#_on_fix_done'))
endfunction

" Analyze vibe
function! crucibai#analyze_vibe()
    call crucibai#_show_status('Analyzing vibe...')

    let code = join(getline(1, '$'), '\n')
    let file_path = expand('%:p')

    let data = {
        \ 'code': code,
        \ 'file_path': file_path
    \ }

    call crucibai#_make_request('POST', '/api/analyze-vibe', data, function('crucibai#_on_vibe_done'))
endfunction

" Voice input
function! crucibai#voice_input()
    if !g:crucibai_enable_voice
        echo 'Voice input is disabled'
        return
    endif

    call crucibai#_show_status('Listening...')

    let data = {'duration': 15}
    call crucibai#_make_request('POST', '/api/voice-input', data, function('crucibai#_on_voice_done'))
endfunction

" Generate tests
function! crucibai#generate_tests()
    call crucibai#_show_status('Generating tests...')

    let code = join(getline(1, '$'), '\n')
    let language = &filetype
    let file_path = expand('%:p')

    let data = {
        \ 'code': code,
        \ 'language': language,
        \ 'file_path': file_path
    \ }

    call crucibai#_make_request('POST', '/api/generate-tests', data, function('crucibai#_on_tests_done'))
endfunction

" Refactor code
function! crucibai#refactor()
    call crucibai#_show_status('Refactoring...')

    let code = join(getline(1, '$'), '\n')
    let language = &filetype

    let data = {
        \ 'code': code,
        \ 'language': language
    \ }

    call crucibai#_make_request('POST', '/api/refactor', data, function('crucibai#_on_refactor_done'))
endfunction

" Generate documentation
function! crucibai#generate_docs()
    call crucibai#_show_status('Generating documentation...')

    let code = join(getline(1, '$'), '\n')
    let language = &filetype
    let file_path = expand('%:p')

    let data = {
        \ 'code': code,
        \ 'language': language,
        \ 'file_path': file_path
    \ }

    call crucibai#_make_request('POST', '/api/generate-docs', data, function('crucibai#_on_docs_done'))
endfunction

" Analyze file
function! crucibai#analyze_file()
    let code = join(getline(1, '$'), '\n')
    let language = &filetype
    let file_path = expand('%:p')

    let data = {
        \ 'code': code,
        \ 'language': language,
        \ 'file_path': file_path
    \ }

    call crucibai#_make_request('POST', '/api/analyze', data, function('crucibai#_on_analyze_done'))
endfunction

" Show settings
function! crucibai#show_settings()
    echo 'CrucibAI Settings:'
    echo 'API URL: ' . g:crucibai_api_url
    echo 'API Key: ' . (empty(g:crucibai_api_key) ? 'Not set' : '***')
    echo 'Auto-analyze: ' . (g:crucibai_auto_analyze ? 'On' : 'Off')
    echo 'Voice input: ' . (g:crucibai_enable_voice ? 'On' : 'Off')
endfunction

" Show status
function! crucibai#show_status()
    call crucibai#_make_request('GET', '/api/health', {}, function('crucibai#_on_status_done'))
endfunction

" ============================================================================
" Internal Functions
" ============================================================================

" Make HTTP request
function! crucibai#_make_request(method, endpoint, data, callback)
    if has('nvim')
        call crucibai#_make_request_nvim(a:method, a:endpoint, a:data, a:callback)
    else
        call crucibai#_make_request_vim(a:method, a:endpoint, a:data, a:callback)
    endif
endfunction

" Make request in Neovim
function! crucibai#_make_request_nvim(method, endpoint, data, callback)
    let url = g:crucibai_api_url . a:endpoint
    let headers = {
        \ 'Authorization': 'Bearer ' . g:crucibai_api_key,
        \ 'Content-Type': 'application/json'
    \ }

    let body = empty(a:data) ? '' : json_encode(a:data)

    call jobstart(['curl', '-X', a:method, '-H', 'Authorization: Bearer ' . g:crucibai_api_key, 
                   '-H', 'Content-Type: application/json', 
                   '-d', body, url], {
        \ 'on_stdout': function('crucibai#_on_response', [a:callback]),
        \ 'on_stderr': function('crucibai#_on_error'),
        \ 'stdout_buffered': v:true
    \ })
endfunction

" Make request in Vim
function! crucibai#_make_request_vim(method, endpoint, data, callback)
    let url = g:crucibai_api_url . a:endpoint
    let body = empty(a:data) ? '' : json_encode(a:data)

    let cmd = 'curl -s -X ' . a:method . 
              \ ' -H "Authorization: Bearer ' . g:crucibai_api_key . '" ' .
              \ ' -H "Content-Type: application/json" ' .
              \ ' -d ' . shellescape(body) . ' ' . url

    let response = system(cmd)
    call a:callback(json_decode(response))
endfunction

" Response handler
function! crucibai#_on_response(callback, job_id, data, event)
    if len(a:data) > 0
        let response = json_decode(join(a:data, ''))
        call a:callback(response)
    endif
endfunction

" Error handler
function! crucibai#_on_error(job_id, data, event)
    echo 'CrucibAI Error: ' . join(a:data, ' ')
endfunction

" Callbacks
function! crucibai#_on_generate_done(response)
    if has_key(a:response, 'code')
        call append(line('.'), split(a:response.code, '\n'))
        call crucibai#_show_status('✅ Code generated')
    else
        call crucibai#_show_status('❌ Generation failed')
    endif
endfunction

function! crucibai#_on_fix_done(response)
    if has_key(a:response, 'fixed_code')
        let start = line('v')
        let end = line('.')
        call deletebufline(bufnr('%'), start, end)
        call append(start - 1, split(a:response.fixed_code, '\n'))
        call crucibai#_show_status('✅ Code fixed')
    else
        call crucibai#_show_status('❌ Fix failed')
    endif
endfunction

function! crucibai#_on_vibe_done(response)
    if has_key(a:response, 'vibe_name')
        let msg = '🎨 Vibe: ' . a:response.vibe_name . 
                  \ ' | 📊 Tone: ' . a:response.emotional_tone .
                  \ ' | ⚡ Energy: ' . a:response.visual_energy
        call crucibai#_show_status(msg)
    else
        call crucibai#_show_status('❌ Analysis failed')
    endif
endfunction

function! crucibai#_on_voice_done(response)
    if has_key(a:response, 'text')
        echo 'Transcribed: ' . a:response.text
        if has_key(a:response, 'code_suggestion')
            call append(line('.'), split(a:response.code_suggestion, '\n'))
            call crucibai#_show_status('✅ Code inserted from voice')
        endif
    else
        call crucibai#_show_status('❌ Voice input failed')
    endif
endfunction

function! crucibai#_on_tests_done(response)
    if has_key(a:response, 'test_code')
        new
        call append(0, split(a:response.test_code, '\n'))
        call crucibai#_show_status('✅ Tests generated')
    else
        call crucibai#_show_status('❌ Test generation failed')
    endif
endfunction

function! crucibai#_on_refactor_done(response)
    if has_key(a:response, 'refactored_code')
        call deletebufline(bufnr('%'), 1, '$')
        call append(0, split(a:response.refactored_code, '\n'))
        call crucibai#_show_status('✅ Refactored')
    else
        call crucibai#_show_status('❌ Refactoring failed')
    endif
endfunction

function! crucibai#_on_docs_done(response)
    if has_key(a:response, 'documentation')
        new
        call append(0, split(a:response.documentation, '\n'))
        call crucibai#_show_status('✅ Documentation generated')
    else
        call crucibai#_show_status('❌ Documentation generation failed')
    endif
endfunction

function! crucibai#_on_analyze_done(response)
    if has_key(a:response, 'quality_score')
        call crucibai#_show_status('Quality: ' . a:response.quality_score . '/10')
    endif
endfunction

function! crucibai#_on_status_done(response)
    if has_key(a:response, 'status')
        echo '✅ CrucibAI Connected'
    else
        echo '❌ CrucibAI Disconnected'
    endif
endfunction

" Helper functions
function! crucibai#_show_status(message)
    echom 'CrucibAI: ' . a:message
endfunction

function! crucibai#_get_selected_text()
    if mode() =~# "[Vv]"
        let [line_start, col_start] = getpos("'<")[1:2]
        let [line_end, col_end] = getpos("'>")[1:2]
        let lines = getline(line_start, line_end)
        if len(lines) == 0
            return ''
        endif
        let lines[-1] = lines[-1][:col_end - 1]
        let lines[0] = lines[0][col_start - 1:]
        return join(lines, '\n')
    else
        return ''
    endif
endfunction
