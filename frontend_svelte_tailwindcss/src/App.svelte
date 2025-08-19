<script lang="ts">
  import QueryForm from './lib/QueryForm.svelte'
  import type { EventRecord, QueryPayload } from './lib/types'
  
  let lastQuery: QueryPayload | null = null
  let queryCount = 0

  function handleQuerySuccess(event: CustomEvent<{ results: EventRecord[], query: QueryPayload }>) {
    lastQuery = event.detail.query
    queryCount++
    console.log('Query successful:', event.detail)
  }

  function handleQueryError(event: CustomEvent<{ error: string }>) {
    console.error('Query failed:', event.detail.error)
  }
</script>

<div class="min-h-screen bg-gray-50">
  <header class="bg-white shadow">
    <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between">
        <h1 class="text-3xl font-bold text-gray-900">Data Extraction API</h1>
        <div class="flex items-center space-x-4">
          {#if queryCount > 0}
            <span class="text-sm text-gray-500">
              {queryCount} {queryCount === 1 ? 'query' : 'queries'} executed
            </span>
          {/if}
        </div>
      </div>
    </div>
  </header>

  <main class="py-8">
    <QueryForm 
      on:querySuccess={handleQuerySuccess}
      on:queryError={handleQueryError}
    />
  </main>

  <footer class="bg-white border-t border-gray-200 mt-12">
    <div class="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
      <div class="text-center text-sm text-gray-500">
        <p>Built with Svelte, TypeScript, Tailwind CSS, and FastAPI</p>
        {#if lastQuery}
          <p class="mt-1">
            Last query: ID {lastQuery.id} from {lastQuery.fromDate} to {lastQuery.toDate}
          </p>
        {/if}
      </div>
    </div>
  </footer>
</div>
