/**
 * DWG → DXF 批量转换脚本
 * 使用 libredwg WASM (Node.js ESM)
 * 
 * 用法: node tests/dwg_to_dxf.mjs <input_dir>
 */
import { LibreDwg } from '@mlightcad/libredwg-web';
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'fs';
import { join, basename, extname } from 'path';

const inputDir = process.argv[2] || 'tests/e2e';

async function convertFile(dwgPath, dxfPath) {
    const data = readFileSync(dwgPath);
    const ld = await LibreDwg.create();
    const dxf = ld.dwg_write_dxf(data);
    if (dxf) {
        writeFileSync(dxfPath, Buffer.from(dxf));
        return true;
    }
    return false;
}

async function main() {
    const files = readdirSync(inputDir).filter(f => extname(f).toLowerCase() === '.dwg');
    console.log(`待转换: ${files.length}个DWG文件\n`);

    let ok = 0, skip = 0, fail = 0;
    for (const f of files) {
        const dwgPath = join(inputDir, f);
        const dxfPath = join(inputDir, f.replace(/\.dwg$/i, '.dxf'));
        const sizeMB = statSync(dwgPath).size / 1024 / 1024;

        if (existsSync(dxfPath) && statSync(dxfPath).size > 10000) {
            console.log(`[${sizeMB.toFixed(1)}MB] ${f} → 跳过(已存在)`);
            skip++;
            continue;
        }

        console.log(`[${sizeMB.toFixed(1)}MB] ${f} → 转换中...`);
        try {
            const result = await convertFile(dwgPath, dxfPath);
            if (result) {
                const dxfSize = statSync(dxfPath).size / 1024;
                console.log(`  ✅ 成功 (${dxfSize.toFixed(0)}KB)`);
                ok++;
            } else {
                console.log(`  ❌ 转换返回空`);
                fail++;
            }
        } catch (e) {
            console.log(`  ❌ 错误: ${e.message}`);
            fail++;
        }
    }

    console.log(`\n成功: ${ok}, 跳过: ${skip}, 失败: ${fail}`);
}

main().catch(e => { console.error(e); process.exit(1); });
