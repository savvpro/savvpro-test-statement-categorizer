export const MAX_BYTES=5*1024*1024;
export function validateFile(f:File):string|null{if(!f.name.toLowerCase().endsWith(".csv"))return "Unsupported file type. Upload a .csv file.";if(f.size>MAX_BYTES)return "File is larger than 5 MB.";if(f.size===0)return "File is empty.";return null}
