<script lang="ts">
  import { tableFromIPC } from 'apache-arrow';
  import ErrorMonitoring from './lib/ErrorMonitoring.svelte';
  import { reportError, reportExcelError, reportApiError, reportValidationError } from './lib/error-reporter';

  interface QueryPayload {
    id?: string | number | null;
    fromDate?: string | null;
    toDate?: string | null;
    environment?: string | null;
  }

  interface QueryResponse {
    data: any[];
    count: number;
    query_info: any;
  }

  // Individual form fields
  let idValue: string = '';
  let fromDateValue: string = '';
  let toDateValue: string = '';
  let environmentValue: string = '';
  
  let isLoading = false;
  let errorMessage = '';
  let successMessage = '';
  let queryResults: QueryResponse | null = null;
  let showResults = false;
  let featherData: any[] = [];

  const API_BASE_URL = 'https://localhost:8000';

  function validateFormData(): QueryPayload | null {
    try {
      // Convert form fields to payload
      const payload: QueryPayload = {};
      
      // Add ID if provided
      if (idValue.trim()) {
        payload.id = isNaN(Number(idValue)) ? idValue.trim() : Number(idValue);
      }
      
      // Add dates if provided and validate format
      if (fromDateValue.trim()) {
        if (!isValidDateFormat(fromDateValue)) {
          throw new Error('From Date must be in yyyy/mm/dd format');
        }
        payload.fromDate = fromDateValue;
      }
      
      if (toDateValue.trim()) {
        if (!isValidDateFormat(toDateValue)) {
          throw new Error('To Date must be in yyyy/mm/dd format');
        }
        payload.toDate = toDateValue;
      }
      
      // Validate date range
      if (payload.fromDate && payload.toDate) {
        const fromDate = new Date(payload.fromDate.replace(/\//g, '-'));
        const toDate = new Date(payload.toDate.replace(/\//g, '-'));
        if (fromDate > toDate) {
          throw new Error('From Date must be less than or equal to To Date');
        }
      }
      
      // Add environment if provided
      if (environmentValue.trim()) {
        payload.environment = environmentValue.trim();
      }
      
      return payload;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      reportValidationError('form_data', error, {
        idValue: idValue ? '[REDACTED]' : null,
        fromDateValue,
        toDateValue,
        environmentValue
      });
      throw new Error(errorMessage);
    }
  }

  function isValidDateFormat(date: string): boolean {
    const dateRegex = /^\d{4}\/\d{2}\/\d{2}$/;
    if (!dateRegex.test(date)) return false;
    
    try {
      const parts = date.split('/');
      const year = parseInt(parts[0]);
      const month = parseInt(parts[1]);
      const day = parseInt(parts[2]);
      
      const dateObj = new Date(year, month - 1, day);
      return dateObj.getFullYear() === year && 
             dateObj.getMonth() === month - 1 && 
             dateObj.getDate() === day;
    } catch {
      return false;
    }
  }

  async function executeQuery() {
    errorMessage = '';
    successMessage = '';
    isLoading = true;
    queryResults = null;
    featherData = [];
    showResults = false;
    
    let payload: QueryPayload | null = null;

    try {
      payload = validateFormData();
      
      const response = await fetch(`${API_BASE_URL}/api/query/feather`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      // Process the Feather binary response
      const featherBytes = await response.arrayBuffer();
      const featherTable = tableFromIPC(new Uint8Array(featherBytes));
      
      // Convert Arrow table to JavaScript objects
      const rows: any[] = [];
      for (let i = 0; i < featherTable.numRows; i++) {
        const row: any = {};
        featherTable.schema.fields.forEach((field, fieldIndex) => {
          const column = featherTable.getChildAt(fieldIndex);
          row[field.name] = column?.get(i);
        });
        rows.push(row);
      }

      featherData = rows;
      
      // Create a compatible QueryResponse object for the UI
      queryResults = {
        data: rows,
        count: rows.length,
        query_info: {
          id: payload!.id?.toString() || null,
          fromDate: payload!.fromDate || null,
          toDate: payload!.toDate || null,
          environment: payload!.environment || null,
          format: 'feather'
        }
      };

      showResults = true;
      successMessage = `Query completed successfully. Found ${rows.length} record(s). File size: ${featherBytes.byteLength} bytes.`;
      
    } catch (error) {
      const errorMessage_ = error instanceof Error ? error.message : String(error);
      errorMessage = `Query failed: ${errorMessage_}`;
      
      reportApiError('/api/query/feather', error, {
        payload: payload ? {
          id: payload.id ? '[REDACTED]' : null,
          fromDate: payload.fromDate,
          toDate: payload.toDate,
          environment: payload.environment
        } : null
      });
    } finally {
      isLoading = false;
    }
  }

  async function updateExcelSheet() {
    const dataToExport = featherData;
    
    if (!dataToExport || dataToExport.length === 0) {
      errorMessage = 'No data available to export to Excel';
      return;
    }

    try {
      // Check if Office.js is available
      if (typeof (globalThis as any).Office === 'undefined') {
        throw new Error('Office.js not available. This feature only works within Excel.');
      }

      const Office = (globalThis as any).Office;
      const Excel = (globalThis as any).Excel;

      await Office.onReady();
      
      await Excel.run(async (context: any) => {
        const worksheet = context.workbook.worksheets.getActiveWorksheet();
        
        // Get the data array with headers
        const headers = Object.keys(dataToExport[0]);
        const dataRows = dataToExport.map(row => headers.map(header => {
          const value = row[header];
          // Handle Date objects and timestamps from Arrow
          if (value instanceof Date) {
            return value.toISOString().split('T')[0];
          } else if (typeof value === 'object' && value !== null && value.toString) {
            return value.toString();
          }
          return value || '';
        }));
        const tableData = [headers, ...dataRows];
        
        // Clear existing content and add new data
        const range = worksheet.getRange('A1').getResizedRange(tableData.length - 1, headers.length - 1);
        range.values = tableData;
        
        // Format the header row
        const headerRange = worksheet.getRange('A1').getResizedRange(0, headers.length - 1);
        headerRange.format.font.bold = true;
        headerRange.format.fill.color = '#4472C4';
        headerRange.format.font.color = 'white';
        
        // Auto-fit columns
        range.format.autofitColumns();
        
        await context.sync();
        
        const recordCount = dataToExport.length;
        successMessage = `Successfully updated Excel sheet with ${recordCount} records`;
        errorMessage = '';
      });
      
    } catch (error) {
      const errorMessage_ = error instanceof Error ? error.message : String(error);
      
      // Provide more specific error messages for common Excel issues
      let userErrorMessage = `Failed to update Excel sheet: ${errorMessage_}`;
      if (errorMessage_.includes('InvalidBinding') || errorMessage_.includes('dimension')) {
        userErrorMessage = 'Failed to update Excel sheet: Data size mismatch. Please try with fewer columns or rows.';
      } else if (errorMessage_.includes('InvalidOperation')) {
        userErrorMessage = 'Failed to update Excel sheet: Invalid operation. Please ensure you have an active worksheet.';
      } else if (errorMessage_.includes('AccessDenied')) {
        userErrorMessage = 'Failed to update Excel sheet: Access denied. Please check worksheet permissions.';
      }
      
      errorMessage = userErrorMessage;
      
      reportExcelError('update_sheet', error, {
        dataRowCount: dataToExport?.length || 0,
        columnCount: dataToExport?.length > 0 ? Object.keys(dataToExport[0]).length : 0,
        formatUsed: 'feather',
        officeAvailable: typeof (globalThis as any).Office !== 'undefined',
        excelAvailable: typeof (globalThis as any).Excel !== 'undefined'
      });
    }
  }

  function clearResults() {
    queryResults = null;
    featherData = [];
    showResults = false;
    errorMessage = '';
    successMessage = '';
    
    // Clear form fields
    idValue = '';
    fromDateValue = '';
    toDateValue = '';
    environmentValue = '';
  }

  function formatJsonValue(value: any): string {
    if (value === null || value === undefined) {
      return '';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  // Example data loading functions
  function loadExample(key: string) {
    // Clear all fields first
    idValue = '';
    fromDateValue = '';
    toDateValue = '';
    environmentValue = '';
    
    switch (key) {
      case 'all':
        // All fields remain empty
        break;
      case 'byId':
        idValue = '12345';
        break;
      case 'byDate':
        fromDateValue = '2024/01/01';
        toDateValue = '2024/12/31';
        break;
      case 'byEnvironment':
        environmentValue = 'production';
        break;
      case 'full':
        idValue = '12345';
        fromDateValue = '2024/01/01';
        toDateValue = '2024/12/31';
        environmentValue = 'production';
        break;
    }
  }
</script>

<main class="max-w-4xl mx-auto p-6 space-y-6">
  <header class="text-center border-b pb-6">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">Data Extraction Tool</h1>
    <p class="text-gray-600">Query your data using filters and export results to Excel</p>
  </header>

  <!-- Quick Examples -->
  <section class="bg-gray-50 p-4 rounded-lg">
    <h3 class="text-lg font-medium text-gray-900 mb-3">Quick Examples</h3>
    <div class="flex flex-wrap gap-2">
      <button class="btn-secondary text-sm" on:click={() => loadExample('all')}>All Data</button>
      <button class="btn-secondary text-sm" on:click={() => loadExample('byId')}>By ID</button>
      <button class="btn-secondary text-sm" on:click={() => loadExample('byDate')}>By Date Range</button>
      <button class="btn-secondary text-sm" on:click={() => loadExample('byEnvironment')}>By Environment</button>
      <button class="btn-secondary text-sm" on:click={() => loadExample('full')}>Full Filter</button>
    </div>
  </section>


  <!-- Filter Input Section -->
  <section class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">Query Filters</h2>
      <button class="btn-secondary text-sm" on:click={clearResults}>Clear Results</button>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label for="id-input" class="block text-sm font-medium text-gray-700 mb-2">
          ID (optional)
        </label>
        <input
          id="id-input"
          type="text"
          bind:value={idValue}
          class="form-input"
          placeholder="Enter ID (e.g., 12345)"
        />
      </div>
      
      <div>
        <label for="environment-input" class="block text-sm font-medium text-gray-700 mb-2">
          Environment (optional)
        </label>
        <input
          id="environment-input"
          type="text"
          bind:value={environmentValue}
          class="form-input"
          placeholder="Enter environment (e.g., production)"
        />
      </div>
      
      <div>
        <label for="from-date-input" class="block text-sm font-medium text-gray-700 mb-2">
          From Date (optional)
        </label>
        <input
          id="from-date-input"
          type="text"
          bind:value={fromDateValue}
          class="form-input"
          placeholder="yyyy/mm/dd (e.g., 2024/01/01)"
          pattern="[0-9]{4}/[0-9]{2}/[0-9]{2}"
        />
      </div>
      
      <div>
        <label for="to-date-input" class="block text-sm font-medium text-gray-700 mb-2">
          To Date (optional)
        </label>
        <input
          id="to-date-input"
          type="text"
          bind:value={toDateValue}
          class="form-input"
          placeholder="yyyy/mm/dd (e.g., 2024/12/31)"
          pattern="[0-9]{4}/[0-9]{2}/[0-9]{2}"
        />
      </div>
    </div>
    
    <p class="text-xs text-gray-500 mt-2">
      All fields are optional. Leave empty for unbounded queries. Dates must be in yyyy/mm/dd format.
    </p>

    <div class="flex gap-3">
      <button
        class="btn-primary"
        on:click={executeQuery}
        disabled={isLoading}
      >
        {#if isLoading}
          <span class="inline-flex items-center">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Fetching Data...
          </span>
        {:else}
          Execute Query
        {/if}
      </button>
      
      {#if queryResults && queryResults.data.length > 0}
        <button class="btn-secondary" on:click={updateExcelSheet}>
          📊 Update Excel Sheet
        </button>
      {/if}
    </div>
  </section>

  <!-- Messages -->
  {#if errorMessage}
    <div class="alert-error">
      <strong>Error:</strong> {errorMessage}
    </div>
  {/if}

  {#if successMessage}
    <div class="alert-success">
      <strong>Success:</strong> {successMessage}
    </div>
  {/if}

  <!-- Results Section -->
  {#if showResults && queryResults}
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-gray-900">Query Results</h2>
        <div class="text-sm text-gray-600">
          {queryResults.count} record(s) found
        </div>
      </div>

      <!-- Query Info -->
      <div class="bg-blue-50 p-4 rounded-lg">
        <h3 class="text-sm font-medium text-blue-900 mb-2">Query Information</h3>
        <div class="text-xs text-blue-800 space-y-1">
          {#if queryResults.query_info.id}
            <div><strong>ID:</strong> {queryResults.query_info.id}</div>
          {/if}
          {#if queryResults.query_info.fromDate}
            <div><strong>From Date:</strong> {queryResults.query_info.fromDate}</div>
          {/if}
          {#if queryResults.query_info.toDate}
            <div><strong>To Date:</strong> {queryResults.query_info.toDate}</div>
          {/if}
          {#if queryResults.query_info.environment}
            <div><strong>Environment:</strong> {queryResults.query_info.environment}</div>
          {/if}
          {#if !queryResults.query_info.id && !queryResults.query_info.fromDate && !queryResults.query_info.toDate && !queryResults.query_info.environment}
            <div><em>No filters applied - showing all data</em></div>
          {/if}
        </div>
      </div>

      <!-- Data Table -->
      {#if queryResults.data.length > 0}
        <div class="overflow-x-auto">
          <table class="results-table">
            <thead>
              <tr>
                {#each Object.keys(queryResults.data[0]) as header}
                  <th>{header}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each queryResults.data as row}
                <tr>
                  {#each Object.keys(queryResults.data[0]) as header}
                    <td>{formatJsonValue(row[header])}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center py-8 text-gray-500">
          <p class="text-lg">No data found matching your query</p>
          <p class="text-sm">Try adjusting your filter conditions</p>
        </div>
      {/if}
    </section>
  {/if}
</main>

<!-- Error monitoring component (no visual output) -->
<ErrorMonitoring />
