import { defineConfig, type Plugin, type UserConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { resolve } from "path";
import fs from "fs";

interface HttpsOptions {
  key: Buffer | string;
  cert: Buffer | string;
  ca?: Buffer | string;
}

interface FunctionsMetadata {
  functions: any[];
}

// 開発用証明書の取得（office-addin-dev-certsの代替）
async function getHttpsOptions(): Promise<HttpsOptions> {
  try {
    // office-addin-dev-certsがある場合は使用
    const devCerts = await import("office-addin-dev-certs");
    const httpsOptions = await devCerts.getHttpsServerOptions();
    return {
      key: httpsOptions.key,
      cert: httpsOptions.cert,
      ca: httpsOptions.ca,
    };
  } catch (error) {
    // フォールバック: 自己署名証明書のパスを指定
    return {
      key: fs.readFileSync("./certs/localhost-key.pem"),
      cert: fs.readFileSync("./certs/localhost-cert.pem"),
    };
  }
}

// Custom Functions用のプラグイン
function customFunctionsPlugin(): Plugin {
  return {
    name: "custom-functions-metadata",
    buildStart() {
      // Custom Functions のメタデータ生成ロジック
      // 実際の実装では custom-functions-metadata-plugin の機能を再現
      console.log("Generating custom functions metadata...");
    },
    generateBundle() {
      // functions.json を生成
      const functionsMetadata: FunctionsMetadata = {
        functions: [],
        // ここで functions.ts を解析してメタデータを生成
      };
      this.emitFile({
        type: "asset",
        fileName: "functions.json",
        source: JSON.stringify(functionsMetadata, null, 2),
      });
    },
  };
}

// マニフェストファイルの変換プラグイン
function manifestTransformPlugin(): Plugin {
  const urlDev = "https://localhost:3000/";
  const urlProd = "https://www.contoso.com/";

  return {
    name: "manifest-transform",
    generateBundle(options) {
      // manifest*.xml ファイルを処理
      const manifestFiles = fs
        .readdirSync(".")
        .filter(
          (file: string) =>
            file.startsWith("manifest") && file.endsWith(".xml"),
        );

      manifestFiles.forEach((file: string) => {
        let content = fs.readFileSync(file, "utf8");

        if (process.env.NODE_ENV !== "development") {
          content = content.replace(
            new RegExp(urlDev + "(?:public/)?", "g"),
            urlProd,
          );
        }
        this.emitFile({
          type: "asset",
          fileName: file,
          source: content,
        });
      });
    },
  };
}

export default defineConfig(async ({ command, mode }): Promise<UserConfig> => {
  const isDev = mode === "development";
  const httpsOptions = await getHttpsOptions();

  return {
    plugins: [
      svelte({
        compilerOptions: {
          dev: isDev,
        },
      }),
      customFunctionsPlugin(),
      manifestTransformPlugin(),
    ],

    // ビルド設定
    build: {
      rollupOptions: {
        output: {
          // アセットのファイル名パターン
          assetFileNames: (assetInfo) => {
            if (
              assetInfo.name &&
              /\.(png|jpg|jpeg|gif|ico)$/.test(assetInfo.name)
            ) {
              return "assets/[name][extname]";
            }
            return "assets/[name]-[hash][extname]";
          },
        },
      },
      sourcemap: true,
      outDir: "dist",
      emptyOutDir: true,
    },

    // 開発サーバーの設定
    server: {
      port: Number(process.env.npm_package_config_dev_server_port) || 3000,
      https: httpsOptions,
      headers: {
        "Access-Control-Allow-Origin": "*",
      },
      fs: {
        strict: false,
      },
    },

    // 依存関係の最適化
    optimizeDeps: {
      include: ["core-js/stable", "regenerator-runtime/runtime"],
    },

    // パス解決の設定
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
      },
    },

    // アセットの処理
    publicDir: "assets",

    // TypeScript設定
    esbuild: {
      target: "es2020",
    },
  };
});