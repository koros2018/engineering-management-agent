#!/usr/bin/env node
/**
 * DWG → DXF 转换脚本 (libredwg WASM)
 * 用法: node convert_dwg.mjs <input.dwg> <output.dxf>
 */
import { LibreDwg } from '@mlightcad/libredwg-web';
import { readFileSync, writeFileSync } from 'fs';

const [dwgPath, outPath] = process.argv.slice(2);
if (!dwgPath || !outPath) {
    console.error('用法: node convert_dwg.mjs <input.dwg> <output.dxf>');
    process.exit(1);
}

async function convert() {
    try {
        const inputData = readFileSync(dwgPath);
        console.error(`读取: ${dwgPath} (${(inputData.length/1024/1024).toFixed(1)}MB)`);
        
        const dwg = await LibreDwg.create();
        const result = dwg.dwg_write_dxf(inputData);
        
        if (result) {
            writeFileSync(outPath, Buffer.from(result));
            console.error(`写入: ${outPath} (${(result.length/1024).toFixed(0)}KB)`);
            console.log('CONVERT_OK');
        } else {
            console.error('CONVERT_FAILED: dwg_write_dxf returned null');
            process.exit(1);
        }
    } catch (e) {
        console.error('ERROR:', e.message);
        process.exit(1);
    }
}

convert();
