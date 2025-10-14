<script lang="ts">
  import { onMount } from 'svelte'


  import './App.css'
  import wasmUrl from 'arrow-rs-wasm/arrow_rs_wasm_bg.wasm?url'   // ← Vite の ?url

  // Import arrow-rs-wasm
  import init, {
    create_test_table,
    write_table_to_ipc,
    read_table_from_bytes,
    get_table_info,
    free_table,
    init_with_options
  } from 'arrow-rs-wasm'

  let count = 0
  let wasmLoaded = false
  let testResults: string[] = []
  let isRunning = false

  function addResult(message: string) {
    // Svelteは配列のpushだけでは再描画されないので、新配列を代入
    testResults = [...testResults, `${new Date().toLocaleTimeString()}: ${message}`]
  }

  // Initialize WASM module on component mount
  onMount(async () => {
    try {
      await init(wasmUrl)
      init_with_options(true)
      wasmLoaded = true
      addResult('✅ WASM module loaded successfully!')
    } catch (error) {
      addResult(`❌ Failed to load WASM module: ${error}`)
    }
  })

  async function runArrowTest() {
    if (!wasmLoaded || isRunning) return

    isRunning = true
    testResults = []

    try {
      addResult('🧪 Starting Arrow WASM test in Vite + Svelte...')

      // 1. Create test table
      addResult('1. Creating test table...')
      const tableHandle = create_test_table()
      addResult(`✅ Test table created (handle: ${tableHandle})`)

      // 2. Get table info
      addResult('2. Getting table information...')
      const tableInfo = get_table_info(tableHandle)
      addResult(`✅ Table: ${tableInfo.row_count} rows, ${tableInfo.column_count} columns`)
      addResult(`   Columns: ${tableInfo.column_names.join(', ')}`)

      // 3. Write to IPC format
      addResult('3. Serializing to Arrow IPC format...')
      const ipcData = write_table_to_ipc(tableHandle, true)
      const uncompressedData = write_table_to_ipc(tableHandle, false)
      const ratio = ((ipcData.length / uncompressedData.length) * 100).toFixed(1)
      addResult(`✅ Serialized: ${ipcData.length} bytes (${ratio}% compression)`)

      // 4. Read data back
      addResult('4. Reading data back...')
      const newTableHandle = read_table_from_bytes(ipcData)
      const newTableInfo = get_table_info(newTableHandle)
      addResult(`✅ Round-trip successful: ${newTableInfo.row_count} rows, ${newTableInfo.column_count} columns`)

      // 5. Clean up
      addResult('5. Cleaning up memory...')
      free_table(tableHandle)
      free_table(newTableHandle)
      addResult('✅ Memory cleaned up')

      addResult('🎉 All Vite + Svelte tests passed!')
    } catch (error) {
      addResult(`❌ Test failed: ${error}`)
    } finally {
      isRunning = false
    }
  }
</script>

<!-- UI -->


<h1>Vite + Svelte + Arrow WASM</h1>

<div class="card">
  <button on:click={() => (count = count + 1)}>
    count is {count}
  </button>

  <div style="margin: 20px 0;">
    <h3>Arrow WASM Test</h3>
    <p>
      WASM Status:
      <span style="color: {wasmLoaded ? 'green' : 'red'};">
        {wasmLoaded ? '✅ Loaded' : '❌ Not Loaded'}
      </span>
    </p>

    <button
      on:click={runArrowTest}
      disabled={!wasmLoaded || isRunning}
      style="
        background-color: {wasmLoaded && !isRunning ? '#007cba' : '#ccc'};
        cursor: {wasmLoaded && !isRunning ? 'pointer' : 'not-allowed'};
      "
    >
      {isRunning ? 'Running Test...' : 'Run Arrow WASM Test'}
    </button>

    {#if testResults.length > 0}
      <div
        style="
          margin-top: 10px;
          padding: 10px;
          background-color: #000;
          color: #00ff00;
          font-family: monospace;
          font-size: 12px;
          border-radius: 5px;
          height: 200px;
          overflow-y: auto;
        "
      >
        {#each testResults as result, index}
          <div>{result}</div>
        {/each}
      </div>
    {/if}
  </div>

  <p>
    Edit <code>src/App.svelte</code> and save to test HMR
  </p>
</div>

<p class="read-the-docs">
  Click on the Vite and Svelte logos to learn more
</p>

<style>
  /* React の App.css を使う場合はこの <style> は不要。
     ここでは最小限のサンプル。 */
  .logo {
    height: 6em;
    padding: 1.5em;
    will-change: filter;
    transition: filter 300ms;
  }
  .logo:hover { filter: drop-shadow(0 0 2em #646cffaa); }
  .logo.react:hover { filter: drop-shadow(0 0 2em #61dafbaa); }
  .card { padding: 2em; }
  .read-the-docs { color: #888; }
</style>
