// ExcelDataWriter.ts
import * as arrow from 'apache-arrow';

interface ColumnInfo {
  name: string;
  type: 'date' | 'string';
  index: number;
}

class ExcelDataWriter {
  private readonly BATCH_SIZE = 10000; // バッチサイズ（行数）
  private readonly MAX_CELLS_PER_UPDATE = 100000; // 1回の更新での最大セル数

  /**
   * Featherファイルからデータを読み込みExcelに書き込む
   */
  async writeFeatherToExcel(
    featherData: ArrayBuffer,
    startCell: string = "A1"
  ): Promise<void> {
    try {
      // Apache Arrowテーブルの読み込み
      const table = arrow.tableFromIPC(featherData);
      
      await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getActiveWorksheet();
        
        // 列情報の取得
        const columnInfo = this.getColumnInfo(table);
        
        // ヘッダーの書き込み
        await this.writeHeaders(sheet, columnInfo, startCell, context);
        
        // データの書き込み（バッチ処理）
        await this.writeDataInBatches(sheet, table, columnInfo, startCell, context);
        
        console.log(`データ書き込み完了: ${table.numRows}行 × ${table.numCols}列`);
      });
    } catch (error) {
      console.error("データ書き込みエラー:", error);
      throw error;
    }
  }

  /**
   * 列情報を取得
   */
  private getColumnInfo(table: arrow.Table): ColumnInfo[] {
    const columns: ColumnInfo[] = [];
    
    table.schema.fields.forEach((field, index) => {
      let type: 'date' | 'string' = 'string';
      
      // データ型の判定
      if (field.type instanceof arrow.DateDay || 
          field.type instanceof arrow.DateMillisecond ||
          field.type instanceof arrow.TimestampSecond ||
          field.type instanceof arrow.TimestampMillisecond) {
        type = 'date';
      }
      
      columns.push({
        name: field.name,
        type: type,
        index: index
      });
    });
    
    return columns;
  }

  /**
   * ヘッダーの書き込み
   */
  private async writeHeaders(
    sheet: Excel.Worksheet,
    columnInfo: ColumnInfo[],
    startCell: string,
    context: Excel.RequestContext
  ): Promise<void> {
    const headers = columnInfo.map(col => col.name);
    const headerRange = sheet.getRange(startCell).getResizedRange(0, headers.length - 1);
    headerRange.values = [headers];
    
    // ヘッダーのフォーマット
    headerRange.format.font.bold = true;
    headerRange.format.fill.color = "#E8E8E8";
    
    await context.sync();
  }

  /**
   * データをバッチで書き込み
   */
  private async writeDataInBatches(
    sheet: Excel.Worksheet,
    table: arrow.Table,
    columnInfo: ColumnInfo[],
    startCell: string,
    context: Excel.RequestContext
  ): Promise<void> {
    const totalRows = table.numRows;
    const totalCols = table.numCols;
    const startRow = this.getCellRow(startCell) + 1; // ヘッダーの次の行から
    const startCol = this.getCellColumn(startCell);
    
    // 列ごとにバッチ処理を行う（メモリ効率を考慮）
    const colBatchSize = Math.floor(this.MAX_CELLS_PER_UPDATE / this.BATCH_SIZE);
    
    for (let colStart = 0; colStart < totalCols; colStart += colBatchSize) {
      const colEnd = Math.min(colStart + colBatchSize, totalCols);
      
      for (let rowStart = 0; rowStart < totalRows; rowStart += this.BATCH_SIZE) {
        const rowEnd = Math.min(rowStart + this.BATCH_SIZE, totalRows);
        const batchData = this.extractBatchData(
          table, 
          rowStart, 
          rowEnd, 
          colStart, 
          colEnd, 
          columnInfo
        );
        
        // Rangeの取得と値の設定
        const range = sheet.getRangeByIndexes(
          startRow + rowStart,
          startCol + colStart,
          rowEnd - rowStart,
          colEnd - colStart
        );
        
        range.values = batchData;
        
        // 日付列のフォーマット設定
        this.formatDateColumns(range, columnInfo, colStart, colEnd);
        
        // 定期的に同期（メモリ解放のため）
        if ((rowStart / this.BATCH_SIZE) % 5 === 0) {
          await context.sync();
          console.log(`進捗: ${rowStart + this.BATCH_SIZE}/${totalRows} 行処理完了`);
        }
      }
    }
    
    await context.sync();
  }

  /**
   * バッチデータの抽出
   */
  private extractBatchData(
    table: arrow.Table,
    rowStart: number,
    rowEnd: number,
    colStart: number,
    colEnd: number,
    columnInfo: ColumnInfo[]
  ): any[][] {
    const batchData: any[][] = [];
    
    for (let i = rowStart; i < rowEnd; i++) {
      const row: any[] = [];
      
      for (let j = colStart; j < colEnd; j++) {
        const column = table.getChildAt(j);
        const value = column?.get(i);
        
        if (columnInfo[j].type === 'date' && value != null) {
          // 日付型の変換
          row.push(this.convertToExcelDate(value));
        } else {
          // 文字列型または null
          row.push(value ?? "");
        }
      }
      
      batchData.push(row);
    }
    
    return batchData;
  }

  /**
   * 日付をExcel形式に変換
   */
  private convertToExcelDate(value: any): number {
    let date: Date;
    
    if (value instanceof Date) {
      date = value;
    } else if (typeof value === 'number') {
      date = new Date(value);
    } else {
      date = new Date(value.toString());
    }
    
    // ExcelのシリアルDate形式に変換
    const excelEpoch = new Date(1900, 0, 1);
    const msPerDay = 24 * 60 * 60 * 1000;
    const excelDate = (date.getTime() - excelEpoch.getTime()) / msPerDay + 2;
    
    return excelDate;
  }

  /**
   * 日付列のフォーマット設定
   */
  private formatDateColumns(
    range: Excel.Range,
    columnInfo: ColumnInfo[],
    colStart: number,
    colEnd: number
  ): void {
    for (let i = colStart; i < colEnd; i++) {
      if (columnInfo[i].type === 'date') {
        const colIndex = i - colStart;
        const dateColumn = range.getColumn(colIndex);
        dateColumn.numberFormat = "yyyy/mm/dd";
      }
    }
  }

  /**
   * セルアドレスから行番号を取得
   */
  private getCellRow(cellAddress: string): number {
    const match = cellAddress.match(/\d+/);
    return match ? parseInt(match[0]) - 1 : 0;
  }

  /**
   * セルアドレスから列番号を取得
   */
  private getCellColumn(cellAddress: string): number {
    const match = cellAddress.match(/[A-Z]+/);
    if (!match) return 0;
    
    let column = 0;
    const letters = match[0];
    
    for (let i = 0; i < letters.length; i++) {
      column = column * 26 + (letters.charCodeAt(i) - 64);
    }
    
    return column - 1;
  }
}

/**
 * 使用例
 */
async function loadFeatherData(): Promise<void> {
  try {
    // バックエンドからFeatherデータを取得
    const response = await fetch('/api/data/export', {
      method: 'GET',
      headers: {
        'Accept': 'application/octet-stream'
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // ArrayBufferとして取得
    const featherData = await response.arrayBuffer();
    
    // ExcelDataWriterのインスタンス作成
    const writer = new ExcelDataWriter();
    
    // データの書き込み
    await writer.writeFeatherToExcel(featherData, "A1");
    
    // 完了通知
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      sheet.activate();
      await context.sync();
    });
    
    console.log("データのインポートが完了しました");
    
  } catch (error) {
    console.error("データ読み込みエラー:", error);
    // エラーをユーザーに通知
    Office.context.ui.displayDialogAsync(
      'error.html?message=' + encodeURIComponent(error.message),
      { height: 30, width: 20 }
    );
  }
}

// Office.jsの初期化後に実行
Office.onReady((info) => {
  if (info.host === Office.HostType.Excel) {
    // ボタンクリックイベントなどでloadFeatherData()を呼び出す
    document.getElementById("importButton")?.addEventListener("click", loadFeatherData);
  }
});
