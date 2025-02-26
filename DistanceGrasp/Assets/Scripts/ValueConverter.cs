using System;
using UnityEngine;

public class ValueConverter
{
    static public int ArrayToLong(ref byte[] arr, int currentPointer, out long value)
    {
        value = BitConverter.ToInt64(arr, currentPointer);
        currentPointer += 8;
        return currentPointer;
    }

    static public int ArrayToInt(ref byte[] arr, int currentPointer, out int value)
    {
        value = BitConverter.ToInt32(arr, currentPointer);
        currentPointer += 4;
        return currentPointer;
    }

    static public int ArrayToFloat(ref byte[] arr, int currentPointer, out float value)
    {
        value = BitConverter.ToSingle(arr, currentPointer);
        currentPointer += 4;
        return currentPointer;
    }

    static public int ArrayToQuaternion(ref byte[] arr, int currentPointer, out Quaternion value)
    {
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.x);
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.y);
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.z);
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.w);
        return currentPointer;
    }

    static public int ArrayToVector3(ref byte[] arr, int currentPointer, out Vector3 value)
    {
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.x);
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.y);
        currentPointer = ArrayToFloat(ref arr, currentPointer, out value.z);
        return currentPointer;
    }

    static public int AddLongToArray(ref byte[] arr, int currentPointer, long value)
    {
        Buffer.BlockCopy(BitConverter.GetBytes(value), 0, arr, currentPointer, 8);
        currentPointer += 8;
        return currentPointer;
    }

    static public int AddIntToArray(ref byte[] arr, int currentPointer, int value)
    {
        Buffer.BlockCopy(BitConverter.GetBytes(value), 0, arr, currentPointer, 4);
        currentPointer += 4;
        return currentPointer;
    }

    static public int AddFloatToArray(ref byte[] arr, int currentPointer, float value)
    {
        Buffer.BlockCopy(BitConverter.GetBytes(value), 0, arr, currentPointer, 4);
        currentPointer += 4;
        return currentPointer;
    }

    static public int AddQuaternionToArray(ref byte[] arr, int currentPointer, Quaternion value)
    {
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.x);
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.y);
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.z);
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.w);
        return currentPointer;
    }

    static public int AddVector3ToArray(ref byte[] arr, int currentPointer, Vector3 value)
    {
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.x);
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.y);
        currentPointer = AddFloatToArray(ref arr, currentPointer, value.z);
        return currentPointer;
    }
}
