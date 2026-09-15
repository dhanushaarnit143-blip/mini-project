import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Strict Scientific Language Compliance', () => {
  const FORBIDDEN_PHRASES = [
    "parkinson's disease detected",
    "patient has parkinson's",
    "cure",
    "treatment recommendation",
  ];

  function getAllFiles(dirPath: string, arrayOfFiles: string[] = []): string[] {
    const files = fs.readdirSync(dirPath);
    files.forEach((file) => {
      const fullPath = path.join(dirPath, file);
      if (fs.statSync(fullPath).isDirectory()) {
        if (!fullPath.includes('node_modules') && !fullPath.includes('.git')) {
          getAllFiles(fullPath, arrayOfFiles);
        }
      } else if (
        (file.endsWith('.ts') || file.endsWith('.tsx')) &&
        !file.includes('language_compliance.test.ts')
      ) {
        arrayOfFiles.push(fullPath);
      }
    });
    return arrayOfFiles;
  }

  it('contains zero occurrences of forbidden diagnostic claims in frontend codebase', () => {
    const srcDir = path.resolve(__dirname, '..');
    const sourceFiles = getAllFiles(srcDir);
    expect(sourceFiles.length).toBeGreaterThan(5);

    const violations: { file: string; phrase: string }[] = [];

    for (const filePath of sourceFiles) {
      const content = fs.readFileSync(filePath, 'utf-8').toLowerCase();
      for (const phrase of FORBIDDEN_PHRASES) {
        if (content.includes(phrase)) {
          violations.push({ file: path.basename(filePath), phrase });
        }
      }
    }

    expect(violations).toEqual([]);
  });
});
